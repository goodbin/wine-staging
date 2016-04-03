import sys
try:
    from cStringIO import StringIO
except ImportError:
    from io import StringIO

        self.patch_author       = header.get('author', None)
        self.patch_email        = header.get('email', None)
        self.patch_subject      = header.get('subject', None)
        self.patch_revision     = header.get('revision', 1)
        self.signed_off_by      = header.get('signedoffby', [])
        self.is_binary          = False
    def read(self):
        """Return the full patch as a string."""
        return "".join(chunk for chunk in self.read_chunks())

    def __init__(self, filename, fp=None):
        self.fp       = fp if fp is not None else open(filename)
def _read_single_patch(fp, header, oldname=None, newname=None):
    """Internal function to read a single patch from a file."""
    patch = PatchObject(fp.filename, header)
    patch.offset_begin = fp.tell()
    patch.oldname = oldname
    patch.newname = newname
    # Skip over initial diff --git header
    line = fp.peek()
    if line.startswith("diff --git "):
        fp.read()
    # Read header
    while True:
        if line is None:
            break
        elif line.startswith("--- "):
            patch.oldname = line[4:].strip()
        elif line.startswith("+++ "):
            patch.newname = line[4:].strip()
        elif line.startswith("old mode") or line.startswith("deleted file mode"):
            pass # ignore
        elif line.startswith("new mode "):
            patch.newmode = line[9:].strip()
        elif line.startswith("new file mode "):
            patch.newmode = line[14:].strip()
        elif line.startswith("new mode") or line.startswith("new file mode"):
            raise PatchParserError("Unable to parse header line '%s'." % line)
        elif line.startswith("copy from") or line.startswith("copy to"):
            raise NotImplementedError("Patch copy header not implemented yet.")
        elif line.startswith("rename "):
            raise NotImplementedError("Patch rename header not implemented yet.")
        elif line.startswith("similarity index") or line.startswith("dissimilarity index"):
            pass # ignore
        elif line.startswith("index "):
            r = re.match("^index ([a-fA-F0-9]*)\.\.([a-fA-F0-9]*)", line)
            if not r: raise PatchParserError("Unable to parse index header line '%s'." % line)
            patch.oldsha1, patch.newsha1 = r.group(1), r.group(2)
        else:
            break
        fp.read()

    if patch.oldname is None or patch.newname is None:
        raise PatchParserError("Missing old or new name.")
    elif patch.oldname == "/dev/null" and patch.newname == "/dev/null":
        raise PatchParserError("Old and new name is /dev/null?")

    if patch.oldname.startswith("a/"):
        patch.oldname = patch.oldname[2:]
    elif patch.oldname != "/dev/null":
        raise PatchParserError("Old name in patch doesn't start with a/.")

    if patch.newname.startswith("b/"):
        patch.newname = patch.newname[2:]
    elif patch.newname != "/dev/null":
        raise PatchParserError("New name in patch doesn't start with b/.")

    if patch.newname != "/dev/null":
        patch.modified_file = patch.newname
    else:
        patch.modified_file = patch.oldname

    # Decide between binary and textual patch
    if line is None or line.startswith("diff --git ") or line.startswith("--- "):
        if oldname != newname:
            raise PatchParserError("Stripped old- and new name doesn't match.")

    elif line.startswith("@@ -"):
        while True:
            line = fp.peek()
            if line is None or not line.startswith("@@ -"):
            r = re.match("^@@ -(([0-9]+),)?([0-9]+) \+(([0-9]+),)?([0-9]+) @@", line)
            if not r: raise PatchParserError("Unable to parse hunk header '%s'." % line)
            srcpos = max(int(r.group(2)) - 1, 0) if r.group(2) else 0
            dstpos = max(int(r.group(5)) - 1, 0) if r.group(5) else 0
            srclines, dstlines = int(r.group(3)), int(r.group(6))
            if srclines <= 0 and dstlines <= 0:
                raise PatchParserError("Empty hunk doesn't make sense.")
            fp.read()
            try:
                while srclines > 0 or dstlines > 0:
                    line = fp.read()[0]
                    if line == " ":
                        if srclines == 0 or dstlines == 0:
                            raise PatchParserError("Corrupted patch.")
                        srclines -= 1
                        dstlines -= 1
                    elif line == "-":
                        if srclines == 0:
                            raise PatchParserError("Corrupted patch.")
                        srclines -= 1
                    elif line == "+":
                        if dstlines == 0:
                            raise PatchParserError("Corrupted patch.")
                        dstlines -= 1
                    elif line == "\\":
                        pass # ignore
                    else:
                        raise PatchParserError("Unexpected line in hunk.")
            except TypeError: # triggered by None[0]
                raise PatchParserError("Truncated patch.")
                if line is None or not line.startswith("\\ "): break
                fp.read()

    elif line.rstrip() == "GIT binary patch":
        if patch.oldsha1 is None or patch.newsha1 is None:
            raise PatchParserError("Missing index header, sha1 sums required for binary patch.")
        elif patch.oldname != patch.newname:
            raise PatchParserError("Stripped old- and new name doesn't match for binary patch.")
        fp.read()

        line = fp.read()
        if line is None: raise PatchParserError("Unexpected end of file.")
        r = re.match("^(literal|delta) ([0-9]+)", line)
        if not r: raise NotImplementedError("Only literal/delta patches are supported.")
        patch.is_binary = True

        # Skip over patch data
        while True:
            if line is None or line.strip() == "":
                break
    else:
        raise PatchParserError("Unknown patch format.")
    patch.offset_end = fp.tell()
    return patch
def _parse_author(author):
    if sys.version_info[0] > 2:
        author = str(email.header.make_header(email.header.decode_header(author)))
    else:
    r =  re.match("\"?([^\"]*)\"? <(.*)>", author)
    if r is None: raise NotImplementedError("Failed to parse From - header.")
    return r.group(1).strip(), r.group(2).strip()

def _parse_subject(subject):
    version = "(v|try|rev|take) *([0-9]+)"
    subject = subject.strip()
    if subject.endswith("."): subject = subject[:-1]
    r = re.match("^\\[PATCH([^]]*)\\](.*)$", subject, re.IGNORECASE)
    if r is not None:
        subject = r.group(2).strip()
        r = re.search(version, r.group(1), re.IGNORECASE)
        if r is not None: return subject, int(r.group(2))
    r = re.match("^(.*)\\(%s\\)$" % version, subject, re.IGNORECASE)
    if r is not None: return r.group(1).strip(), int(r.group(3))
    r = re.match("^(.*)\\[%s\\]$" % version, subject, re.IGNORECASE)
    if r is not None: return r.group(1).strip(), int(r.group(3))
    r = re.match("^(.*)[.,] +%s$" % version, subject, re.IGNORECASE)
    if r is not None: return r.group(1).strip(), int(r.group(3))
    r = re.match("^([^:]+) %s: (.*)$" % version, subject, re.IGNORECASE)
    if r is not None: return "%s: %s" % (r.group(1), r.group(4)), int(r.group(3))
    r = re.match("^(.*) +%s$" % version, subject, re.IGNORECASE)
    if r is not None: return r.group(1).strip(), int(r.group(3))
    r = re.match("^(.*)\\(resend\\)$", subject, re.IGNORECASE)
    if r is not None: return r.group(1).strip(), 1
    return subject, 1

def read_patch(filename, fp=None):
    """Iterates over all patches contained in a file, and returns PatchObject objects."""
    with _FileReader(filename, fp) as fp:
                header.pop('signedoffby', None)
                fp.read()
                fp.read()
                    fp.read()
                header.pop('signedoffby', None)
                if 'signedoffby' not in header:
                fp.read()
                fp.read()
    result = tempfile.NamedTemporaryFile(mode='w+', delete=False)
        return tempfile._TemporaryFileWrapper(file=open(result.name, 'r+'), \
    with tempfile.NamedTemporaryFile(mode='w+') as diff:
            if line.startswith("\\ "):
                continue
    with tempfile.NamedTemporaryFile(mode='w+') as intermediate:
        diff = tempfile.NamedTemporaryFile(mode='w+')

if __name__ == "__main__":
    import unittest

    # Basic tests for _parse_author() and _parse_subject()
    class PatchParserTests(unittest.TestCase):
        def test_author(self):
            author = _parse_author("Author Name <author@email.com>")
            self.assertEqual(author, ("Author Name", "author@email.com"))

            author = _parse_author("=?UTF-8?q?Author=20Name?= <author@email.com>")
            self.assertEqual(author, ("Author Name", "author@email.com"))

        def test_subject(self):
            subject = _parse_subject("[PATCH v3] component: Subject.")
            self.assertEqual(subject, ("component: Subject", 3))

            subject = _parse_subject("[PATCH] component: Subject (v3).")
            self.assertEqual(subject, ("component: Subject", 3))

            subject = _parse_subject("[PATCH] component: Subject (try 3).")
            self.assertEqual(subject, ("component: Subject", 3))

            subject = _parse_subject("[PATCH] component: Subject (take 3).")
            self.assertEqual(subject, ("component: Subject", 3))

            subject = _parse_subject("[PATCH] component: Subject (rev 3).")
            self.assertEqual(subject, ("component: Subject", 3))

            subject = _parse_subject("[PATCH] component: Subject [v3].")
            self.assertEqual(subject, ("component: Subject", 3))

            subject = _parse_subject("[PATCH] component: Subject, v3.")
            self.assertEqual(subject, ("component: Subject", 3))

            subject = _parse_subject("[PATCH] component: Subject v3.")
            self.assertEqual(subject, ("component: Subject", 3))

            subject = _parse_subject("[PATCH] component: Subject (resend).")
            self.assertEqual(subject, ("component: Subject", 1))

    # Basic tests for read_patch()
    class PatchReaderTests(unittest.TestCase):
        def test_read(self):
            source = ["From be07df750862699f2515c0ac0ceb7a6c25e9458a Mon Sep 17 00:00:00 2001",
                      "From: =?UTF-8?q?Author=20Name?= <author@email.com>",
                      "Subject: [PATCH v3] component: Replace arg1 with arg2.",
                      "",
                      "Signed-off-by: =?UTF-8?q?Author=20Name?= <author@email.com>",
                      "Signed-off-by: Other Developer <other@email.com>",
                      "---",
                      " test.txt | 2 +-",
                      " 1 file changed, 1 insertion(+), 1 deletion(-)",
                      "",
                      "diff --git a/test.txt b/test.txt",
                      "index d54375d..0078e66 100644",
                      "--- a/test.txt", "+++ b/test.txt",
                      "@@ -1,7 +1,7 @@",
                      " line1();", " line2();", " line3();",
                      "-function(arg1);",
                      "+function(arg2);",
                      " line5();", " line6();", " line7();",
                      "-- ",
                      "2.7.1"]

            expected = ["diff --git a/test.txt b/test.txt",
                        "index d54375d..0078e66 100644",
                        "--- a/test.txt", "+++ b/test.txt",
                        "@@ -1,7 +1,7 @@",
                        " line1();", " line2();", " line3();",
                        "-function(arg1);",
                        "+function(arg2);",
                        " line5();", " line6();", " line7();"]

            # Test formatted git patch with author and subject
            patchfile = tempfile.NamedTemporaryFile(mode='w+')
            patchfile.write("\n".join(source + [""]))
            patchfile.flush()

            patches = list(read_patch(patchfile.name))
            self.assertEqual(len(patches), 1)
            self.assertEqual(patches[0].patch_author,   "Author Name")
            self.assertEqual(patches[0].patch_email,    "author@email.com")
            self.assertEqual(patches[0].patch_subject,  "component: Replace arg1 with arg2.")
            self.assertEqual(patches[0].patch_revision, 3)
            self.assertEqual(patches[0].signed_off_by,  [("Author Name", "author@email.com"),
                                                         ("Other Developer", "other@email.com")])
            self.assertEqual(patches[0].filename,       patchfile.name)
            self.assertEqual(patches[0].is_binary,      False)
            self.assertEqual(patches[0].modified_file,  "test.txt")

            lines = patches[0].read().rstrip("\n").split("\n")
            self.assertEqual(lines, expected)

            # Test with git diff
            del source[0:10]
            self.assertTrue(source[0].startswith("diff --git"))
            patchfile = tempfile.NamedTemporaryFile(mode='w+')
            patchfile.write("\n".join(source + [""]))
            patchfile.flush()

            patches = list(read_patch(patchfile.name))
            self.assertEqual(len(patches), 1)
            self.assertEqual(patches[0].patch_author,   None)
            self.assertEqual(patches[0].patch_email,    None)
            self.assertEqual(patches[0].patch_subject,  None)
            self.assertEqual(patches[0].patch_revision, 1)
            self.assertEqual(patches[0].signed_off_by,  [])
            self.assertEqual(patches[0].filename,       patchfile.name)
            self.assertEqual(patches[0].is_binary,      False)
            self.assertEqual(patches[0].modified_file, "test.txt")

            lines = patches[0].read().rstrip("\n").split("\n")
            self.assertEqual(lines, expected)

            # Test with unified diff
            del source[0:2]
            self.assertTrue(source[0].startswith("---"))
            patchfile = tempfile.NamedTemporaryFile(mode='w+')
            patchfile.write("\n".join(source + [""]))
            patchfile.flush()

            patches = list(read_patch(patchfile.name))
            self.assertEqual(len(patches), 1)
            self.assertEqual(patches[0].patch_author,   None)
            self.assertEqual(patches[0].patch_email,    None)
            self.assertEqual(patches[0].patch_subject,  None)
            self.assertEqual(patches[0].patch_revision, 1)
            self.assertEqual(patches[0].signed_off_by,  [])
            self.assertEqual(patches[0].filename,       patchfile.name)
            self.assertEqual(patches[0].is_binary,      False)
            self.assertEqual(patches[0].modified_file,  "test.txt")

            del expected[0:2]
            lines = patches[0].read().rstrip("\n").split("\n")
            self.assertEqual(lines, expected)

            # Test with StringIO buffer
            fp = StringIO("\n".join(source + [""]))
            patches = list(read_patch("unknown.patch", fp))
            self.assertEqual(len(patches), 1)
            self.assertEqual(patches[0].patch_author,   None)
            self.assertEqual(patches[0].patch_email,    None)
            self.assertEqual(patches[0].patch_subject,  None)
            self.assertEqual(patches[0].patch_revision, 1)
            self.assertEqual(patches[0].signed_off_by,  [])
            self.assertEqual(patches[0].filename,       "unknown.patch")
            self.assertEqual(patches[0].is_binary,      False)
            self.assertEqual(patches[0].modified_file,  "test.txt")

    # Basic tests for apply_patch()
    class PatchApplyTests(unittest.TestCase):
        def test_apply(self):
            source = ["line1();", "line2();", "line3();",
                      "function(arg1);",
                      "line5();", "line6();", "line7();"]
            original = tempfile.NamedTemporaryFile(mode='w+')
            original.write("\n".join(source + [""]))
            original.flush()

            source = ["@@ -1,7 +1,7 @@",
                      " line1();", " line2();", " line3();",
                      "-function(arg1);",
                      "+function(arg2);",
                      " line5();", " line6();", " line7();"]
            patchfile = tempfile.NamedTemporaryFile(mode='w+')
            patchfile.write("\n".join(source + [""]))
            patchfile.flush()

            expected = ["line1();", "line2();", "line3();",
                        "function(arg2);",
                        "line5();", "line6();", "line7();"]
            result = apply_patch(original, patchfile, fuzz=0)
            lines = result.read().rstrip("\n").split("\n")
            self.assertEqual(lines, expected)

            expected = ["line1();", "line2();", "line3();",
                        "function(arg1);",
                        "line5();", "line6();", "line7();"]
            result = apply_patch(result, patchfile, reverse=True, fuzz=0)
            lines = result.read().rstrip("\n").split("\n")
            self.assertEqual(lines, expected)

    # Basic tests for _preprocess_source()
    class PreprocessorTests(unittest.TestCase):
        def test_preprocessor(self):
            source = ["int a; // comment 1",
                      "int b; // comment 2 \\",
                      "          comment 3 \\",
                      "          comment 4",
                      "int c; // comment with \"quotes\"",
                      "int d; // comment with /* c++ comment */",
                      "int e; /* multi \\",
                      "          line",
                      "          comment */",
                      "char *x = \"\\\\\";",
                      "char *y = \"abc\\\"def\";",
                      "char *z = \"multi\" \\",
                      "          \"line\"",
                      "          \"string\";"]
            lines, split = _preprocess_source(source)
            self.assertEqual(lines, source)
            self.assertEqual(split, set([0, 1, 4, 5, 6, 9, 10, 11, 13, 14]))

    # Basic tests for generate_ifdef_patch()
    class GenerateIfdefPatchTests(unittest.TestCase):
        def test_ifdefined(self):
            source = ["line1();", "line2();", "line3();",
                      "function(arg1, \\",
                      "         arg2, \\",
                      "         arg3);",
                      "line5();", "line6();", "line7();"]
            source1 = tempfile.NamedTemporaryFile(mode='w+')
            source1.write("\n".join(source + [""]))
            source1.flush()

            source = ["line1();", "line2();", "line3();",
                      "function(arg1, \\",
                      "         new_arg2, \\",
                      "         arg3);",
                      "line5();", "line6();", "line7();"]
            source2  = tempfile.NamedTemporaryFile(mode='w+')
            source2.write("\n".join(source + [""]))
            source2.flush()

            diff = generate_ifdef_patch(source1, source1, "PATCHED")
            self.assertEqual(diff, None)

            diff = generate_ifdef_patch(source2, source2, "PATCHED")
            self.assertEqual(diff, None)

            expected = ["@@ -1,9 +1,15 @@",
                        " line1();", " line2();", " line3();",
                        "+#if defined(PATCHED)",
                        " function(arg1, \\",
                        "          new_arg2, \\",
                        "          arg3);",
                        "+#else  /* PATCHED */",
                        "+function(arg1, \\",
                        "+         arg2, \\",
                        "+         arg3);",
                        "+#endif /* PATCHED */",
                        " line5();", " line6();", " line7();"]
            diff = generate_ifdef_patch(source1, source2, "PATCHED")
            lines = diff.read().rstrip("\n").split("\n")
            self.assertEqual(lines, expected)

            expected = ["@@ -1,9 +1,15 @@",
                        " line1();", " line2();", " line3();",
                        "+#if defined(PATCHED)",
                        " function(arg1, \\",
                        "          arg2, \\",
                        "          arg3);",
                        "+#else  /* PATCHED */",
                        "+function(arg1, \\",
                        "+         new_arg2, \\",
                        "+         arg3);",
                        "+#endif /* PATCHED */",
                        " line5();", " line6();", " line7();"]
            diff = generate_ifdef_patch(source2, source1, "PATCHED")
            lines = diff.read().rstrip("\n").split("\n")
            self.assertEqual(lines, expected)

    unittest.main()