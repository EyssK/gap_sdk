APP = test
APP_SRCS += test.c ov5640_config.c
APP_CFLAGS += -O3 -g
APP_LDFLAGS += -g -lgaplib

#APP_CFLAGS += -DHIMAX
#APP_CFLAGS += -DDEBUG
#APP_CFLAGS += -DJPEG

override config_args += --config-opt=camera/image-stream=$(CURDIR)/imgTest0.pgm
override config_args += --config-opt=runner/peripherals=true

clean::
	rm -rf output*

include $(RULES_DIR)/pmsis_rules.mk
