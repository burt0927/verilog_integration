#include "exm_dpi.h"
#include "vltstd/svdpi.h"

void exm_message(example::levels level, const char* formatted) {
  svScope scope = svGetScope();
  const char* filename = "";
  int line = 0;
  if (svGetCallerInfo(&filename, &line) == 0) {
    INTERNAL("svGetCallerInfo failed");
  };

  const char* scope_name = svGetNameFromScope(scope);
  example::message::instance()->emit(level, (char*)filename, line, (char*)formatted, NULL);
}

#define SEVERITY(level, LEVEL) \
  void level(const char* formatted) { \
    exm_message(example::LEVEL, formatted); \
  }

SEVERITY(exm_int_debug,   INT_DEBUG)
SEVERITY(exm_debug,       DEBUG)
SEVERITY(exm_information, INFORMATION)
SEVERITY(exm_error,       ERROR)
SEVERITY(exm_fatal,       FATAL)

#undef SEVERITY
