$(function() {
    function OctoPrusaCamViewModel(parameters) {
        var self = this;

        self.settings = parameters[0];

        // Observables
        self.showToken = ko.observable(false);
        self.isTestingSnapshot = ko.observable(false);
        self.isTestingUpload = ko.observable(false);
        self.testFeedbackSuccess = ko.observable(null);
        self.testFeedbackMessage = ko.observable("");
        self.previewImage = ko.observable("");

        self.statusSuccess = ko.observable(null);
        self.statusMessage = ko.observable("Lade Status...");
        self.statusTime = ko.observable("");

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

        self.getEffectiveConfig = function() {
            var s = self.settings.plugins.octoprusacam;
            return {
                token: (s.token ? s.token() : "") || "",
                fingerprint: (s.fingerprint ? s.fingerprint() : "") || "",
                snapshot_url: (s.snapshot_url ? s.snapshot_url() : "") || "",
                snapshot_auth_user: (s.snapshot_auth_user ? s.snapshot_auth_user() : "") || "",
                snapshot_auth_pass: (s.snapshot_auth_pass ? s.snapshot_auth_pass() : "") || "",
                rotate: (s.rotate ? parseInt(s.rotate(), 10) : 0) || 0,
                flip_h: (s.flip_h ? Boolean(s.flip_h()) : false),
                flip_v: (s.flip_v ? Boolean(s.flip_v()) : false)
            };
        };

        self.generateFingerprint = function() {
            OctoPrint.simpleApiCommand("octoprusacam", "generate_fingerprint", {})
                .done(function(response) {
                    if (response && response.fingerprint) {
                        self.settings.plugins.octoprusacam.fingerprint(response.fingerprint);
                    }
                })
                .fail(function() {
                    // Fallback client-side generator
                    var rand = Math.random().toString(16).substring(2, 10) + Math.random().toString(16).substring(2, 10);
                    self.settings.plugins.octoprusacam.fingerprint(rand);
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
                })
                .fail(function() {
                    self.statusSuccess(null);
                    self.statusMessage("Status konnte nicht geladen werden.");
                });
        };

        self.testSnapshotOnly = function() {
            self.clearFeedback();
            self.isTestingSnapshot(true);

            var payload = self.getEffectiveConfig();

            OctoPrint.simpleApiCommand("octoprusacam", "test_snapshot", payload)
                .done(function(response) {
                    self.testFeedbackSuccess(true);
                    self.testFeedbackMessage(response.message || "Snapshot erfolgreich erfasst.");
                    if (response.image_preview) {
                        self.previewImage(response.image_preview);
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
                    self.testFeedbackSuccess(false);
                    self.testFeedbackMessage(errorMsg);
                })
                .always(function() {
                    self.isTestingSnapshot(false);
                });
        };

        self.testUploadPrusa = function() {
            self.clearFeedback();
            self.isTestingUpload(true);

            var payload = self.getEffectiveConfig();

            if (!payload.token || payload.token.trim() === "") {
                self.testFeedbackSuccess(false);
                self.testFeedbackMessage("Bitte zuerst einen Prusa Connect Token eingeben.");
                self.isTestingUpload(false);
                return;
            }

            OctoPrint.simpleApiCommand("octoprusacam", "test_upload", payload)
                .done(function(response) {
                    self.testFeedbackSuccess(true);
                    self.testFeedbackMessage(
                        (response.message || "Snapshot erfolgreich hochgeladen.") +
                        " (HTTP " + (response.status_code || 200) + ")"
                    );
                    if (response.image_preview) {
                        self.previewImage(response.image_preview);
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
                    self.testFeedbackSuccess(false);
                    self.testFeedbackMessage(errorMsg);
                    self.refreshStatus();
                })
                .always(function() {
                    self.isTestingUpload(false);
                });
        };

        self.onSettingsShown = function() {
            self.refreshStatus();
        };
    }

    OCTOPRINT_VIEWMODELS.push({
        construct: OctoPrusaCamViewModel,
        dependencies: ["settingsViewModel"],
        elements: ["#settings_plugin_octoprusacam"]
    });
});
