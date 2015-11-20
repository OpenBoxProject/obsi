#ifndef CLICK_REGEXSET_H_
#define CLICK_REGEXSET_H_
#include <click/string.hh>
#include <click/packet.hh>
#include <re2/re2.h>
#include <re2/set.h>

CLICK_DECLS
class RegexSet {
  public:
    RegexSet();
    ~RegexSet();
    int add_pattern(const String& pattern);
    bool compile();
    void reset();
    bool is_open() const;
    int match_first(const char* data, int length) const;
    int match_first(const String& s) const;
    int match_first(const Packet *p) const;
    bool match_any(const char *data, int length) const;
    bool match_any(const String& s) const;
    bool match_any(const Packet *p) const;


  private:
    bool _compiled;
    re2::RE2::Set *_compiled_regex; 
};

// Match a packet against a set of Regex patterns,
// return the first pattern matched or -1 if no match
inline int RegexSet::match_first(const Packet* p) const{
    return match_first((char*)p->data(), p->length());
}

inline int RegexSet::match_first(const String& s) const {
    return match_first(s.c_str(), s.length());
}

inline int RegexSet::match_first(const char *data, int length) const {
    std::vector<int> matched_patterns;
    re2::StringPiece string_data(data, length);
    if (!_compiled_regex->Match(string_data, &matched_patterns)) {
        return -1; 
    }

    int first_match = matched_patterns[0];
    for (unsigned i=1; i < matched_patterns.size(); ++i) {
        if (matched_patterns[i] < first_match) {
          first_match = matched_patterns[i];
        }
    }

    return first_match;
}

inline bool RegexSet::match_any(const String& s) const {
    return match_any(s.c_str(), s.length());
}

inline bool RegexSet::match_any(const Packet *p) const {
    return match_any((char*) p->data(), p->length());
}

inline bool RegexSet::match_any(const char *data, int length) const {
    std::vector<int> matched_patterns;
    re2::StringPiece string_data(data, length);
    return _compiled_regex->Match(string_data, &matched_patterns);
}


CLICK_ENDDECLS
#endif /* CLICK_REGEXSET_H_ */
