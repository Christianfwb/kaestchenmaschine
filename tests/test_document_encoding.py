"""Check UTF-8 and the known CP932 corruption in German entry documents."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
DOCUMENTS = ('README.md', 'labor/README.md', 'labor/HERKUNFT.md', 'docs/ABSCHLUSS_20261121.md')

def validate(data):
    text = data.decode('utf-8')
    if any('\uff61' <= ch <= '\uff9f' or ch == '\ufffd' for ch in text):
        raise ValueError('Encoding damage in a German entry document')
    return text

class DocumentEncoding(unittest.TestCase):
    def test_german_entry_documents(self):
        for name in DOCUMENTS:
            with self.subTest(path=name):
                validate((ROOT / name).read_bytes())

    def test_detects_valid_utf8_with_corrupted_content(self):
        damaged = 'K\u00e4stchen'.encode('utf-8').decode('cp932').encode('utf-8')
        with self.assertRaises(ValueError):
            validate(damaged)

    def test_accepts_german_utf8(self):
        original = 'K\u00e4stchen, Pr\u00fcfung, Stra\u00dfe, \u00dcberblick'
        self.assertEqual(validate(original.encode('utf-8')), original)

    def test_rejects_invalid_utf8(self):
        with self.assertRaises(UnicodeDecodeError):
            validate(b'\xff')

if __name__ == '__main__':
    unittest.main(verbosity=2)
