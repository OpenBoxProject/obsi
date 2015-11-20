#include <click/config.h>
#include "regexset.hh"
CLICK_DECLS

RegexSet::RegexSet() :
_compiled(false), 
_compiled_regex(new re2::RE2::Set(re2::RE2::Options(), re2::RE2::UNANCHORED)) 
{

}

RegexSet::~RegexSet() {
    if (_compiled_regex) {
        delete _compiled_regex;
    }
}

int RegexSet::add_pattern(const String& pattern) {
  if (!_compiled_regex) {
    return -2; 
  }

  int result = _compiled_regex->Add(re2::StringPiece(pattern.c_str(), pattern.length()), NULL);
  return result;
}

bool RegexSet::compile() {
  if (!_compiled_regex) {
    return false;
  }

  _compiled = _compiled_regex->Compile();
  return _compiled;
}

bool RegexSet::is_open() const {
    return _compiled_regex && !_compiled;
}

void RegexSet::reset() {
    _compiled = false;
    delete _compiled_regex;
    _compiled_regex = new re2::RE2::Set(re2::RE2::Options(), re2::RE2::UNANCHORED);
}

CLICK_ENDDECLS
ELEMENT_REQUIRES(userlevel)
ELEMENT_PROVIDES(RegexSet)
ELEMENT_MT_SAFE(RegexSet)
ELEMENT_LIBS((-L/usr/local/lib -lre2))
