if (ZEPHYR_CURRENT_MODULE_DIR STREQUAL CMAKE_CURRENT_LIST_DIR)
  zephyr_library()
  zephyr_library_sources(src/behavior_extended_caps_word.c)
endif()
