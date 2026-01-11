SOURCE_ADI := wsjtx_log.adi
TARGET_DIR := $(shell dirname $$(readlink -f $(SOURCE_ADI)))
BACKUP := wsjtx_log.adi.backup

check:
	python3 check_qrz_settings.py

folsom:
	@echo "Switching to CM98kq - Folsom, CA (Sacramento County)"
	@echo "Update QRZ settings:"
	@echo "  Grid:   CM98kq"
	@echo "  County: Sacramento"
	@echo "  IOTA:   (remove/blank)"
	@xdg-open "https://www.qrz.com/edit?tab=location" 2>/dev/null || open "https://www.qrz.com/edit?tab=location" 2>/dev/null || echo "Open https://www.qrz.com/edit?tab=location"

freeland:
	@echo "Switching to CN88ra - Freeland, WA (Island County)"
	@echo "Update QRZ settings:"
	@echo "  Grid:   CN88ra"
	@echo "  County: Island"
	@echo "  IOTA:   NA-065"
	@xdg-open "https://www.qrz.com/edit?tab=location" 2>/dev/null || open "https://www.qrz.com/edit?tab=location" 2>/dev/null || echo "Open https://www.qrz.com/edit?tab=location"

go:
	cp "$(TARGET_DIR)/wsjtx_log.adi" "$(BACKUP)"
	@echo "Backed up original to $(BACKUP)"
	python3 split_adi_by_gridsquare.py
	cp *_wsjtx_log.adi "$(TARGET_DIR)/"
	@echo "Copied files to $(TARGET_DIR)"
