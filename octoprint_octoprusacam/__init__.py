# coding=utf-8
from __future__ import absolute_import

import base64
import datetime
import io
import time
import uuid

import flask
import requests

import octoprint.plugin
from octoprint.util import RepeatedTimer


class OctoPrusaCamPlugin(
    octoprint.plugin.StartupPlugin,
    octoprint.plugin.ShutdownPlugin,
    octoprint.plugin.SettingsPlugin,
    octoprint.plugin.AssetPlugin,
    octoprint.plugin.TemplatePlugin,
    octoprint.plugin.SimpleApiPlugin,
    octoprint.plugin.EventHandlerPlugin,
):
    PRUSA_CONNECT_SNAPSHOT_URL = "https://connect.prusa3d.com/c/snapshot"
    PRUSA_CONNECT_INFO_URL = "https://connect.prusa3d.com/c/info"

    def __init__(self):
        self._timer = None
        self._last_status = {
            "success": None,
            "message": "Plugin loaded, waiting for first upload.",
            "timestamp": None,
            "status_code": None,
        }
        self._last_synced_camera_info = None

    # ~~ SettingsPlugin mixin

    def get_settings_defaults(self):
        return {
            "enabled": False,
            "token": "",
            "fingerprint": "",
            "camera_name": "Octoprint Cam",
            "snapshot_url": "",
            "snapshot_timeout": 5,
            "upload_timeout": 10,
            "upload_interval": 10,
            "upload_only_printing": False,
            "snapshot_auth_user": "",
            "snapshot_auth_pass": "",
            "rotate": 0,
            "flip_h": False,
            "flip_v": False,
        }

    def get_settings_restricted_paths(self):
        return {
            "admin": [
                ["token"],
                ["snapshot_auth_pass"],
            ]
        }

    def on_settings_save(self, data):
        old_enabled = self._settings.get_boolean(["enabled"])
        old_interval = self._settings.get_int(["upload_interval"])

        octoprint.plugin.SettingsPlugin.on_settings_save(self, data)

        new_enabled = self._settings.get_boolean(["enabled"])
        new_interval = self._settings.get_int(["upload_interval"])

        token = (self._settings.get(["token"]) or "").strip()
        fingerprint = (self._settings.get(["fingerprint"]) or "").strip()
        camera_name = (self._settings.get(["camera_name"]) or "Octoprint Cam").strip() or "Octoprint Cam"

        if token and fingerprint:
            sync_key = (token, fingerprint, camera_name)
            if self._last_synced_camera_info != sync_key:
                try:
                    self._update_camera_info(token=token, fingerprint=fingerprint, camera_name=camera_name)
                except Exception as e:
                    self._logger.warning("Could not sync camera info on settings save: %s", e)

        if not new_enabled:
            self._stop_timer()
        elif not old_enabled or old_interval != new_interval:
            self._start_timer()

    # ~~ StartupPlugin & ShutdownPlugin mixin

    def on_after_startup(self):
        self._logger.info("OctoPrusaCam plugin started")

        # Auto-generate a unique fingerprint if not set yet
        fingerprint = self._settings.get(["fingerprint"])
        if not fingerprint:
            fingerprint = uuid.uuid4().hex[:16]
            self._settings.set(["fingerprint"], fingerprint)
            self._settings.save()
            self._logger.info("Generated new camera fingerprint: %s", fingerprint)

        if self._settings.get_boolean(["enabled"]):
            self._start_timer()

    def on_shutdown(self):
        self._stop_timer()

    # ~~ Background Timer

    def _start_timer(self):
        self._stop_timer()
        interval = self._settings.get_int(["upload_interval"]) or 10
        if interval < 2:
            interval = 2

        self._timer = RepeatedTimer(interval, self._timer_task, run_first=True)
        self._timer.start()
        self._logger.info("OctoPrusaCam timer started (interval: %ss)", interval)

    def _stop_timer(self):
        if self._timer is not None:
            try:
                self._timer.cancel()
            except Exception as e:
                self._logger.warning("Error cancelling timer: %s", e)
            self._timer = None
            self._logger.info("OctoPrusaCam timer stopped")

    def _timer_task(self):
        if not self._settings.get_boolean(["enabled"]):
            return

        token = (self._settings.get(["token"]) or "").strip()
        if not token:
            self._last_status = {
                "success": False,
                "message": "Upload skipped: Prusa Connect camera token is not configured.",
                "timestamp": time.time(),
                "status_code": None,
            }
            return

        if self._settings.get_boolean(["upload_only_printing"]):
            if not (self._printer.is_printing() or self._printer.is_paused()):
                self._logger.debug("Printer is idle; skipping snapshot upload")
                return

        fingerprint = (self._settings.get(["fingerprint"]) or "").strip()
        if not fingerprint:
            fingerprint = uuid.uuid4().hex[:16]
            self._settings.set(["fingerprint"], fingerprint)
            self._settings.save()

        try:
            image_bytes = self._fetch_snapshot()
            success, status_code, message = self._upload_to_prusa_connect(
                image_bytes=image_bytes,
                token=token,
                fingerprint=fingerprint,
                timeout=self._settings.get_int(["upload_timeout"]) or 10,
            )
            self._last_status = {
                "success": success,
                "message": message,
                "timestamp": time.time(),
                "status_code": status_code,
            }
            if success:
                camera_name = (self._settings.get(["camera_name"]) or "Octoprint Cam").strip() or "Octoprint Cam"
                sync_key = (token, fingerprint, camera_name)
                if self._last_synced_camera_info != sync_key:
                    self._update_camera_info(
                        token=token,
                        fingerprint=fingerprint,
                        camera_name=camera_name,
                        timeout=self._settings.get_int(["upload_timeout"]) or 10,
                    )
            else:
                self._logger.warning("Snapshot upload failed (%s): %s", status_code, message)
        except Exception as e:
            self._logger.error("Exception during snapshot upload: %s", e)
            self._last_status = {
                "success": False,
                "message": str(e),
                "timestamp": time.time(),
                "status_code": None,
            }

    # ~~ Snapshot Acquisition & Processing

    def _resolve_snapshot_url(self, custom_url=None):
        url = (custom_url or self._settings.get(["snapshot_url"]) or "").strip()

        if not url:
            # Fallback 1: OctoPrint classic webcam snapshot
            url = (self._settings.global_get(["webcam", "snapshot"]) or "").strip()
        if not url:
            # Fallback 2: OctoPrint 1.9+ webcam profile snapshot
            url = (self._settings.global_get(["plugins", "classicwebcam", "snapshot"]) or "").strip()
        if not url:
            # Fallback 3: Standard default mjpg-streamer port
            url = "http://127.0.0.1:8080/?action=snapshot"

        if url.startswith("/"):
            # OctoPi uses reverse proxy on port 80 for /webcam/
            url = "http://127.0.0.1" + url

        return url

    def _fetch_snapshot(
        self,
        snapshot_url=None,
        auth_user=None,
        auth_pass=None,
        timeout=None,
        rotate=None,
        flip_h=None,
        flip_v=None,
    ):
        url = self._resolve_snapshot_url(snapshot_url)
        user = auth_user if auth_user is not None else self._settings.get(["snapshot_auth_user"])
        password = auth_pass if auth_pass is not None else self._settings.get(["snapshot_auth_pass"])
        timeout_val = timeout if timeout is not None else (self._settings.get_int(["snapshot_timeout"]) or 5)

        auth = None
        if user and password:
            auth = (user, password)

        response = requests.get(url, auth=auth, timeout=timeout_val, stream=False)
        response.raise_for_status()
        image_bytes = response.content

        # Image post-processing (rotation / flip)
        rot_val = rotate if rotate is not None else (self._settings.get_int(["rotate"]) or 0)
        fh_val = flip_h if flip_h is not None else self._settings.get_boolean(["flip_h"])
        fv_val = flip_v if flip_v is not None else self._settings.get_boolean(["flip_v"])

        if rot_val != 0 or fh_val or fv_val:
            try:
                from PIL import Image, ImageOps

                image = Image.open(io.BytesIO(image_bytes))
                if fh_val:
                    image = ImageOps.mirror(image)
                if fv_val:
                    image = ImageOps.flip(image)
                if rot_val in (90, 180, 270):
                    # Pillow rotate is counter-clockwise, rotate clockwise to match UI expectation
                    image = image.rotate(-rot_val, expand=True)

                out_buf = io.BytesIO()
                image.save(out_buf, format="JPEG", quality=85)
                image_bytes = out_buf.getvalue()
            except ImportError:
                self._logger.warning("Pillow is not installed; skipping image transformation")
            except Exception as ex:
                self._logger.warning("Error transforming image: %s", ex)

        return image_bytes

    # ~~ Prusa Connect Upload

    def _upload_to_prusa_connect(self, image_bytes, token, fingerprint, timeout=10):
        headers = {
            "accept": "*/*",
            "content-type": "image/jpg",
            "fingerprint": str(fingerprint).strip(),
            "token": str(token).strip(),
            "Fingerprint": str(fingerprint).strip(),
            "Token": str(token).strip(),
        }

        try:
            res = requests.put(
                self.PRUSA_CONNECT_SNAPSHOT_URL,
                data=image_bytes,
                headers=headers,
                timeout=timeout,
            )

            if res.status_code in (200, 204):
                return True, res.status_code, "Snapshot uploaded successfully."
            elif res.status_code in (401, 403):
                return (
                    False,
                    res.status_code,
                    "Unauthorized (HTTP {}): Check your Token and Fingerprint in Prusa Connect.".format(
                        res.status_code
                    ),
                )
            elif res.status_code == 400:
                return (
                    False,
                    res.status_code,
                    "Bad Request (HTTP 400): Snapshot rejected by Prusa Connect API.",
                )
            elif res.status_code == 404:
                return (
                    False,
                    res.status_code,
                    "Not Found (HTTP 404): Camera not found in Prusa Connect.",
                )
            else:
                return (
                    False,
                    res.status_code,
                    "Upload failed with HTTP {}: {}".format(res.status_code, res.text[:200]),
                )
        except requests.exceptions.Timeout:
            return False, 408, "Connection to Prusa Connect timed out."
        except requests.exceptions.RequestException as e:
            return False, 500, "Network error uploading snapshot: {}".format(str(e))

    def _update_camera_info(self, token, fingerprint, camera_name="Octoprint Cam", timeout=10):
        name = (camera_name or "Octoprint Cam").strip() or "Octoprint Cam"
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "fingerprint": str(fingerprint).strip(),
            "token": str(token).strip(),
            "Fingerprint": str(fingerprint).strip(),
            "Token": str(token).strip(),
            "Camera-Token": str(token).strip(),
        }
        payload = {
            "config": {
                "name": name,
            },
            "name": name,
            "camera_name": name,
        }
        try:
            res = requests.put(
                self.PRUSA_CONNECT_INFO_URL,
                json=payload,
                headers=headers,
                timeout=timeout,
            )
            if res.status_code in (200, 204):
                self._last_synced_camera_info = (str(token).strip(), str(fingerprint).strip(), name)
                self._logger.info("Updated camera name to '%s' in Prusa Connect", name)
                return True, res.status_code, "Camera name updated successfully."
            else:
                self._logger.warning(
                    "Updating camera info in Prusa Connect returned HTTP %s: %s",
                    res.status_code,
                    res.text[:200],
                )
                return False, res.status_code, "Failed to update camera info (HTTP {})".format(res.status_code)
        except Exception as e:
            self._logger.warning("Exception updating camera info in Prusa Connect: %s", e)
            return False, 500, str(e)

    # ~~ SimpleApiPlugin mixin

    def get_api_commands(self):
        return {
            "test_upload": [],
            "test_snapshot": [],
            "generate_fingerprint": [],
            "get_status": [],
        }

    def on_api_command(self, command, data):
        data = data or {}

        if command == "get_status":
            ts = self._last_status.get("timestamp")
            formatted_time = (
                datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
                if ts
                else "Never"
            )
            return flask.jsonify(
                {
                    "enabled": self._settings.get_boolean(["enabled"]),
                    "camera_name": (self._settings.get(["camera_name"]) or "Octoprint Cam").strip() or "Octoprint Cam",
                    "is_printing": self._printer.is_printing() or self._printer.is_paused(),
                    "resolved_url": self._resolve_snapshot_url(),
                    "last_status": {
                        **self._last_status,
                        "formatted_time": formatted_time,
                    },
                }
            )

        elif command == "generate_fingerprint":
            new_fingerprint = uuid.uuid4().hex[:16]
            return flask.jsonify({"fingerprint": new_fingerprint})

        elif command == "test_snapshot":
            # Test only fetching local snapshot without uploading to Prusa Connect
            snapshot_url = data.get("snapshot_url")
            auth_user = data.get("snapshot_auth_user")
            auth_pass = data.get("snapshot_auth_pass")
            try:
                rotate = int(data.get("rotate", self._settings.get_int(["rotate"]) or 0))
            except (ValueError, TypeError):
                rotate = self._settings.get_int(["rotate"]) or 0
            flip_h = bool(data.get("flip_h", self._settings.get_boolean(["flip_h"])))
            flip_v = bool(data.get("flip_v", self._settings.get_boolean(["flip_v"])))

            try:
                img_bytes = self._fetch_snapshot(
                    snapshot_url=snapshot_url,
                    auth_user=auth_user,
                    auth_pass=auth_pass,
                    rotate=rotate,
                    flip_h=flip_h,
                    flip_v=flip_v,
                )
                b64_img = base64.b64encode(img_bytes).decode("ascii")
                return flask.jsonify(
                    {
                        "success": True,
                        "message": "Snapshot capture successful ({} bytes)".format(len(img_bytes)),
                        "image_preview": "data:image/jpeg;base64," + b64_img,
                    }
                )
            except Exception as e:
                return flask.jsonify(
                    {
                        "success": False,
                        "message": "Failed to capture snapshot: {}".format(str(e)),
                    }
                ), 400

        elif command == "test_upload":
            # Test full cycle: snapshot + upload to Prusa Connect
            token = data.get("token") or self._settings.get(["token"])
            fingerprint = data.get("fingerprint") or self._settings.get(["fingerprint"])
            camera_name = data.get("camera_name") or self._settings.get(["camera_name"]) or "Octoprint Cam"
            snapshot_url = data.get("snapshot_url")
            auth_user = data.get("snapshot_auth_user")
            auth_pass = data.get("snapshot_auth_pass")
            try:
                rotate = int(data.get("rotate", self._settings.get_int(["rotate"]) or 0))
            except (ValueError, TypeError):
                rotate = self._settings.get_int(["rotate"]) or 0
            flip_h = bool(data.get("flip_h", self._settings.get_boolean(["flip_h"])))
            flip_v = bool(data.get("flip_v", self._settings.get_boolean(["flip_v"])))

            if not token:
                return (
                    flask.jsonify(
                        {
                            "success": False,
                            "message": "Prusa Connect Token is required.",
                        }
                    ),
                    400,
                )

            if not fingerprint:
                fingerprint = uuid.uuid4().hex[:16]

            try:
                img_bytes = self._fetch_snapshot(
                    snapshot_url=snapshot_url,
                    auth_user=auth_user,
                    auth_pass=auth_pass,
                    rotate=rotate,
                    flip_h=flip_h,
                    flip_v=flip_v,
                )
            except Exception as e:
                return (
                    flask.jsonify(
                        {
                            "success": False,
                            "message": "Failed to capture local snapshot: {}".format(str(e)),
                        }
                    ),
                    400,
                )

            success, status_code, message = self._upload_to_prusa_connect(
                image_bytes=img_bytes,
                token=token,
                fingerprint=fingerprint,
                timeout=15,
            )

            if success:
                self._update_camera_info(
                    token=token,
                    fingerprint=fingerprint,
                    camera_name=camera_name,
                    timeout=10,
                )

            b64_img = base64.b64encode(img_bytes).decode("ascii")
            return (
                flask.jsonify(
                    {
                        "success": success,
                        "status_code": status_code,
                        "message": message,
                        "image_preview": "data:image/jpeg;base64," + b64_img,
                    }
                ),
                200 if success else 400,
            )

        return flask.jsonify({"error": "Unknown command"}), 404

    # ~~ AssetPlugin mixin

    def get_assets(self):
        return {
            "js": ["js/octoprusacam.js"],
            "css": ["css/octoprusacam.css"],
        }

    # ~~ TemplatePlugin mixin

    def get_template_configs(self):
        return [
            {
                "type": "settings",
                "name": "Prusa Connect Cam",
                "custom_bindings": True,
            }
        ]

    # ~~ Softwareupdate hook

    def get_update_information(self):
        return {
            "octoprusacam": {
                "displayName": "OctoPrusaCam",
                "displayVersion": self._plugin_version,
                "type": "github_release",
                "user": "Snake4you",
                "repo": "OctoPrusaCam",
                "current": self._plugin_version,
                "pip": "https://github.com/Snake4you/OctoPrusaCam/archive/{target_version}.zip",
            }
        }


__plugin_name__ = "OctoPrusaCam"
__plugin_pythoncompat__ = ">=3.7,<4"
__plugin_version__ = "1.0.3"
__plugin_description__ = "Bridge OctoPrint camera snapshots to Prusa Connect Camera API"
__plugin_author__ = "Snake4you"
__plugin_author_email__ = "snake4you@users.noreply.github.com"
__plugin_url__ = "https://github.com/Snake4you/OctoPrusaCam"
__plugin_license__ = "Apache-2.0"


def __plugin_load__():
    global __plugin_implementation__
    __plugin_implementation__ = OctoPrusaCamPlugin()

    global __plugin_hooks__
    __plugin_hooks__ = {
        "octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information
    }
