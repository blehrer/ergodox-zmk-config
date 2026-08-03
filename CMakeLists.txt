# Compile into ZMK's app target so drivers/behavior.h and other app includes resolve.
if (ZEPHYR_CURRENT_MODULE_DIR STREQUAL CMAKE_CURRENT_LIST_DIR)
  target_sources(app PRIVATE src/behavior_extended_caps_word.c)
endif()
