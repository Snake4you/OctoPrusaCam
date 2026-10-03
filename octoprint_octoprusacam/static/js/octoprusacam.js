$(function() {
    function CameraItemViewModel(data, parent) {
        var self = this;
        data = data || {};

        self.id = ko.observable(data.id || ("cam_" + Math.random().toString(36).substring(2, 10)));
        self.name = ko.observable(data.name || "Octoprint Cam");
        self.enabled = ko.observable(data.enabled !== undefined ? Boolean(data.enabled) : true);
        self.token = ko.observable(data.token || "");
        self.fingerprint = ko.observable(data.fingerprint || "");
        self.snapshot_url = ko.observable(data.snapshot_url || "");
        self.snapshot_auth_user = ko.observable(data.snapshot_auth_user || "");
        self.snapshot_auth_pass = ko.observable(data.snapshot_auth_pass || "");
        self.rotate = ko.observable(data.rotate !== undefined ? parseInt(data.rotate, 10) : 0);
        self.flip_h = ko.observable(Boolean(data.flip_h));
        self.flip_v = ko.observable(Boolean(data.flip_v));

        // UI state per camera
        self.showToken = ko.observable(false);
        self.isTestingSnapshot = ko.observable(false);
        self.isTestingUpload = ko.observable(false);
        self.testFeedbackSuccess = ko.observable(null);
        self.testFeedbackMessage = ko.observable("");
        self.previewImage = ko.observable("");
        self.lastStatusSuccess = ko.observable(null);
        self.lastStatusMessage = ko.observable("");
        self.lastStatusTime = ko.observable("");

        self.isTesting = ko.computed(function() {
            return self.isTestingSnapshot() || self.isTestingUpload();
        });

        self.toggleShowToken = function() {
            self.showToken(!self.showToken());
        };

        self.clearFeedback = function() {
            self.testFeedbackSuccess(null);
            self.testFeedbackMessage("");
        };

        self.toJS = function() {
            return {
                id: self.id(),
                name: (self.name() || "Octoprint Cam").trim(),
                camera_name: (self.name() || "Octoprint Cam").trim(),
                enabled: self.enabled(),
                token: (self.token() || "").trim(),
                fingerprint: (self.fingerprint() || "").trim(),
                snapshot_url: (self.snapshot_url() || "").trim(),
                snapshot_auth_user: (self.snapshot_auth_user() || "").trim(),
                snapshot_auth_pass: (self.snapshot_auth_pass() || "").trim(),
                rotate: parseInt(self.rotate(), 10) || 0,
                flip_h: Boolean(self.flip_h()),
                flip_v: Boolean(self.flip_v())
            };
        };
    }

    function OctoPrusaCamViewModel(parameters) {
        var self = this;

        self.settingsViewModel = parameters[0];
        self.settings = null;

        // Multi-Camera List and Selection
        self.cameras = ko.observableArray([]);
        self.selectedCamera = ko.observable(null);

        // Overall status
        self.statusSuccess = ko.observable(null);
        self.statusMessage = ko.observable("Lade Status...");
        self.statusTime = ko.observable("");

        self.getPluginSettings = function() {
            if (self.settingsViewModel && self.settingsViewModel.settings && self.settingsViewModel.settings.plugins && self.settingsViewModel.settings.plugins.octoprusacam) {
                return self.settingsViewModel.settings.plugins.octoprusacam;
            }
            return null;
        };

        self.loadCamerasFromSettings = function() {
            var pSettings = self.getPluginSettings();
            if (!pSettings) return;

            var rawCameras = [];
            if (pSettings.cameras) {
                var cVal = ko.unwrap(pSettings.cameras);
                if (Array.isArray(cVal)) {
                    rawCameras = cVal;
                }
            }

            // Fallback to legacy single-camera settings if cameras array is empty
            if (!rawCameras || rawCameras.length === 0) {
                var legacyName = (pSettings.camera_name ? ko.unwrap(pSettings.camera_name) : "") || "Octoprint Cam";
                var legacyToken = (pSettings.token ? ko.unwrap(pSettings.token) : "") || "";
                var legacyFp = (pSettings.fingerprint ? ko.unwrap(pSettings.fingerprint) : "") || "";
                rawCameras = [{
                    id: "cam_default",
                    name: legacyName,
                    enabled: true,
                    token: legacyToken,
                    fingerprint: legacyFp,
                    snapshot_url: (pSettings.snapshot_url ? ko.unwrap(pSettings.snapshot_url) : "") || "",
                    snapshot_auth_user: (pSettings.snapshot_auth_user ? ko.unwrap(pSettings.snapshot_auth_user) : "") || "",
                    snapshot_auth_pass: (pSettings.snapshot_auth_pass ? ko.unwrap(pSettings.snapshot_auth_pass) : "") || "",
                    rotate: (pSettings.rotate ? ko.unwrap(pSettings.rotate) : 0) || 0,
                    flip_h: (pSettings.flip_h ? ko.unwrap(pSettings.flip_h) : false) || false,
                    flip_v: (pSettings.flip_v ? ko.unwrap(pSettings.flip_v) : false) || false
                }];
            }

            var mapped = [];
            for (var i = 0; i < rawCameras.length; i++) {
                var item = rawCameras[i];
                var cleanItem = {
                    id: ko.unwrap(item.id) || ("cam_" + i),
                    name: ko.unwrap(item.name) || (i === 0 ? "Octoprint Cam" : ("Kamera " + (i + 1))),
                    enabled: item.enabled !== undefined ? Boolean(ko.unwrap(item.enabled)) : true,
                    token: ko.unwrap(item.token) || "",
                    fingerprint: ko.unwrap(item.fingerprint) || "",
                    snapshot_url: ko.unwrap(item.snapshot_url) || "",
                    snapshot_auth_user: ko.unwrap(item.snapshot_auth_user) || "",
                    snapshot_auth_pass: ko.unwrap(item.snapshot_auth_pass) || "",
                    rotate: ko.unwrap(item.rotate) !== undefined ? parseInt(ko.unwrap(item.rotate), 10) : 0,
                    flip_h: Boolean(ko.unwrap(item.flip_h)),
                    flip_v: Boolean(ko.unwrap(item.flip_v))
                };
                mapped.push(new CameraItemViewModel(cleanItem, self));
            }

            self.cameras(mapped);
            if (mapped.length > 0) {
                self.selectedCamera(mapped[0]);
            }
            self.syncToSettings();
        };

        self.syncToSettings = function() {
            var pSettings = self.getPluginSettings();
            if (!pSettings) return;

            var rawList = [];
            ko.utils.arrayForEach(self.cameras(), function(cam) {
                rawList.push(cam.toJS());
            });

            if (pSettings.cameras) {
                pSettings.cameras(rawList);
            }

            // Sync first camera to legacy fields for backward compatibility
            if (rawList.length > 0) {
                var primary = rawList[0];
                if (pSettings.camera_name) pSettings.camera_name(primary.name);
                if (pSettings.token) pSettings.token(primary.token);
                if (pSettings.fingerprint) pSettings.fingerprint(primary.fingerprint);
                if (pSettings.snapshot_url) pSettings.snapshot_url(primary.snapshot_url);
                if (pSettings.snapshot_auth_user) pSettings.snapshot_auth_user(primary.snapshot_auth_user);
                if (pSettings.snapshot_auth_pass) pSettings.snapshot_auth_pass(primary.snapshot_auth_pass);
                if (pSettings.rotate) pSettings.rotate(primary.rotate);
                if (pSettings.flip_h) pSettings.flip_h(primary.flip_h);
                if (pSettings.flip_v) pSettings.flip_v(primary.flip_v);
            }
        };

        self.selectCamera = function(cam) {
            self.selectedCamera(cam);
        };

        self.addCamera = function() {
            var count = self.cameras().length + 1;
            var randFp = Math.random().toString(16).substring(2, 10) + Math.random().toString(16).substring(2, 10);
            var newCam = new CameraItemViewModel({
                id: "cam_" + Math.random().toString(36).substring(2, 10),
                name: "Kamera " + count,
                enabled: true,
                token: "",
                fingerprint: randFp,
                snapshot_url: "",
                snapshot_auth_user: "",
                snapshot_auth_pass: "",
                rotate: 0,
                flip_h: false,
                flip_v: false
            }, self);

            // Fetch an official UUID fingerprint from server
            OctoPrint.simpleApiCommand("octoprusacam", "generate_fingerprint", {})
                .done(function(response) {
                    if (response && response.fingerprint) {
                        newCam.fingerprint(response.fingerprint);
                    }
                });

            self.cameras.push(newCam);
            self.selectedCamera(newCam);
            self.syncToSettings();
        };

        self.duplicateCamera = function(cam) {
            var raw = cam.toJS();
            raw.id = "cam_" + Math.random().toString(36).substring(2, 10);
            raw.name = (raw.name || "Kamera") + " (Kopie)";
            raw.fingerprint = Math.random().toString(16).substring(2, 10) + Math.random().toString(16).substring(2, 10);
            var newCam = new CameraItemViewModel(raw, self);

            OctoPrint.simpleApiCommand("octoprusacam", "generate_fingerprint", {})
                .done(function(response) {
                    if (response && response.fingerprint) {
                        newCam.fingerprint(response.fingerprint);
                    }
                });

            self.cameras.push(newCam);
            self.selectedCamera(newCam);
            self.syncToSettings();
        };

        self.removeCamera = function(cam) {
            if (self.cameras().length <= 1) {
                alert("Mindestens eine Kamera muss konfiguriert bleiben.");
                return;
            }
            var camName = cam.name() || "Unbenannt";
            if (!confirm("Möchtest du die Kamera '" + camName + "' wirklich löschen?")) {
                return;
            }
            var index = self.cameras.indexOf(cam);
            self.cameras.remove(cam);
            if (self.cameras().length > 0) {
                var newIdx = Math.max(0, index - 1);
                self.selectedCamera(self.cameras()[newIdx]);
            } else {
                self.selectedCamera(null);
            }
            self.syncToSettings();
        };

        self.generateFingerprintForCamera = function(cam) {
            OctoPrint.simpleApiCommand("octoprusacam", "generate_fingerprint", {})
                .done(function(response) {
                    if (response && response.fingerprint) {
                        cam.fingerprint(response.fingerprint);
                    }
                })
                .fail(function() {
                    var rand = Math.random().toString(16).substring(2, 10) + Math.random().toString(16).substring(2, 10);
                    cam.fingerprint(rand);
                });
        };

        self.refreshStatus = function() {
            OctoPrint.simpleApiCommand("octoprusacam", "get_status", {})
                .done(function(data) {
                    if (data && data.last_status) {
                        self.statusSuccess(data.last_status.success);
                        self.statusMessage(data.last_status.message || "");
                        self.statusTime(data.last_status.formatted_time || "");
                    }
                    if (data && data.cameras_status) {
                        ko.utils.arrayForEach(self.cameras(), function(cam) {
                            var cs = data.cameras_status[cam.id()];
                            if (cs) {
                                cam.lastStatusSuccess(cs.success);
                                cam.lastStatusMessage(cs.message || "");
                                if (cs.timestamp) {
                                    var d = new Date(cs.timestamp * 1000);
                                    cam.lastStatusTime(d.toLocaleTimeString());
                                }
                            }
                        });
                    }
                })
                .fail(function() {
                    self.statusSuccess(null);
                    self.statusMessage("Status konnte nicht geladen werden.");
                });
        };

        self.testSnapshotForCamera = function(cam) {
            cam.clearFeedback();
            cam.isTestingSnapshot(true);

            var payload = cam.toJS();

            OctoPrint.simpleApiCommand("octoprusacam", "test_snapshot", payload)
                .done(function(response) {
                    cam.testFeedbackSuccess(true);
                    cam.testFeedbackMessage(response.message || "Snapshot erfolgreich erfasst.");
                    if (response.image_preview) {
                        cam.previewImage(response.image_preview);
                    }
                })
                .fail(function(xhr) {
                    var errorMsg = "Fehler beim Abrufen des Snapshots.";
                    try {
                        var res = JSON.parse(xhr.responseText);
                        if (res && res.message) {
                            errorMsg = res.message;
                        }
                    } catch (e) {}
                    cam.testFeedbackSuccess(false);
                    cam.testFeedbackMessage(errorMsg);
                })
                .always(function() {
                    cam.isTestingSnapshot(false);
                });
        };

        self.testUploadForCamera = function(cam) {
            cam.clearFeedback();
            cam.isTestingUpload(true);

            var payload = cam.toJS();

            if (!payload.token || payload.token.trim() === "") {
                cam.testFeedbackSuccess(false);
                cam.testFeedbackMessage("Bitte zuerst einen Prusa Connect Token für diese Kamera eingeben.");
                cam.isTestingUpload(false);
                return;
            }

            OctoPrint.simpleApiCommand("octoprusacam", "test_upload", payload)
                .done(function(response) {
                    cam.testFeedbackSuccess(true);
                    cam.testFeedbackMessage(
                        (response.message || "Snapshot erfolgreich hochgeladen.") +
                        " (HTTP " + (response.status_code || 200) + ")"
                    );
                    if (response.image_preview) {
                        cam.previewImage(response.image_preview);
                    }
                    self.refreshStatus();
                })
                .fail(function(xhr) {
                    var errorMsg = "Fehler beim Upload an Prusa Connect.";
                    try {
                        var res = JSON.parse(xhr.responseText);
                        if (res && res.message) {
                            errorMsg = res.message;
                        }
                    } catch (e) {}
                    cam.testFeedbackSuccess(false);
                    cam.testFeedbackMessage(errorMsg);
                    self.refreshStatus();
                })
                .always(function() {
                    cam.isTestingUpload(false);
                });
        };

        self.onBeforeBinding = function() {
            if (self.settingsViewModel && self.settingsViewModel.settings) {
                self.settings = self.settingsViewModel.settings;
                self.loadCamerasFromSettings();
            }
        };

        self.onSettingsShown = function() {
            if (self.cameras().length === 0) {
                self.loadCamerasFromSettings();
            }
            self.refreshStatus();
        };

        self.onSettingsBeforeSave = function() {
            self.syncToSettings();
        };
    }

    OCTOPRINT_VIEWMODELS.push({
        construct: OctoPrusaCamViewModel,
        dependencies: ["settingsViewModel"],
        elements: ["#settings_plugin_octoprusacam"]
    });
});
