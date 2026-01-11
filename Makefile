# Makefile for WSPR beacon management

# Auto-detect OS and set default device
UNAME_S := $(shell uname -s)
ifeq ($(UNAME_S),Linux)
    DEVICE ?= /dev/ttyUSB0
endif
ifeq ($(UNAME_S),Darwin)
    DEVICE ?= /dev/cu.usbserial-110
endif

# Configuration
BAUD ?= 9600
CALL ?=
GRID ?=
POWER ?=

.PHONY: help test monitor 160m 80m 40m 30m 20m 17m 15m 12m 10m 6m

# Default target - show help
help:
	@echo "WSPR Beacon Management Targets"
	@echo "=============================="
	@echo ""
	@echo "Monitoring:"
	@echo "  make monitor       Connect to serial port to monitor beacon (Ctrl-C to exit)"
	@echo ""
	@echo "Testing:"
	@echo "  make test          Run test suite"
	@echo ""
	@echo "Band Selection (using defaults from config/script):"
	@echo "  make 160m          Switch to 160m band (1838.1 kHz)"
	@echo "  make 80m           Switch to 80m band (3570.1 kHz)"
	@echo "  make 40m           Switch to 40m band (7040.1 kHz)"
	@echo "  make 30m           Switch to 30m band (10140.2 kHz)"
	@echo "  make 20m           Switch to 20m band (14097.1 kHz)"
	@echo "  make 17m           Switch to 17m band (18106.1 kHz)"
	@echo "  make 15m           Switch to 15m band (21096.1 kHz)"
	@echo "  make 12m           Switch to 12m band (24926.1 kHz)"
	@echo "  make 10m           Switch to 10m band (28126.1 kHz)"
	@echo "  make 6m            Switch to 6m band (50294.5 kHz)"
	@echo ""
	@echo "Override parameters:"
	@echo "  make 20m POWER=27              Switch to 20m at 500mW"
	@echo "  make 40m POWER=30              Switch to 40m at 1W"
	@echo "  make 20m CALL=K1ABC GRID=FN42  Use custom callsign and grid"
	@echo ""
	@echo "Configuration:"
	@echo "  DEVICE=$(DEVICE)"
	@echo "  BAUD=$(BAUD)"
	@echo "  CALL=$(if $(CALL),$(CALL),(from config))"
	@echo "  GRID=$(if $(GRID),$(GRID),(from config))"
	@echo "  POWER=$(if $(POWER),$(POWER),(from config))"

# Monitor target - connect to serial port
monitor:
	@./wspr_band.py --monitor -d $(DEVICE) -b $(BAUD)

# Test target
test:
	@echo "Running test suite..."
	@./test_wspr_band.py

# Build command line arguments
ARGS = $(if $(CALL),-c $(CALL)) $(if $(GRID),-g $(GRID)) $(if $(POWER),-p $(POWER)) $(if $(DEVICE),-d $(DEVICE)) $(if $(BAUD),-b $(BAUD))

# Band targets
160m:
	@./wspr_band.py 160m $(ARGS)

80m:
	@./wspr_band.py 80m $(ARGS)

40m:
	@./wspr_band.py 40m $(ARGS)

30m:
	@./wspr_band.py 30m $(ARGS)

20m:
	@./wspr_band.py 20m $(ARGS)

17m:
	@./wspr_band.py 17m $(ARGS)

15m:
	@./wspr_band.py 15m $(ARGS)

12m:
	@./wspr_band.py 12m $(ARGS)

10m:
	@./wspr_band.py 10m $(ARGS)

6m:
	@./wspr_band.py 6m $(ARGS)
