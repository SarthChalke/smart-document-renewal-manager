import unittest
from services.ocr_service import parse_document_text, normalize_date, is_tesseract_available


class OCRTestCase(unittest.TestCase):
    def test_pan_card_text_extraction(self):
        sample_text = """
        INCOME TAX DEPARTMENT
        GOVT. OF INDIA
        Permanent Account Number Card
        ABCDE1234F
        Name: VIGHNESH PATIL
        Date of Birth: 15/08/2002
        Date of Issue: 10/01/2020
        """
        parsed = parse_document_text(sample_text)
        self.assertEqual(parsed['category'], 'pan')
        self.assertEqual(parsed['document_number'], 'ABCDE1234F')
        self.assertIn('Vighnesh Patil', parsed['holder_name'])
        self.assertEqual(parsed['issue_date'], '2020-01-10')

    def test_aadhaar_card_text_extraction(self):
        sample_text = """
        Government of India
        Unique Identification Authority of India
        Enrollment No: 1234/56789/01234
        To: Rahul S. Sharma
        9876 5432 1098
        VID: 1234 5678 9012 3456
        My Aadhaar, My Identity
        """
        parsed = parse_document_text(sample_text)
        self.assertEqual(parsed['category'], 'aadhaar')
        self.assertEqual(parsed['document_number'], '9876 5432 1098')

    def test_driving_licence_and_expiry_detection(self):
        sample_text = """
        UNION OF INDIA
        DRIVING LICENCE
        Licence No: MH14 20180012345
        Name: AMIT VERMA
        Date of Issue: 05-06-2018
        Valid Till: 04-06-2038
        Authorisation to Drive: LMV, MCWG
        """
        parsed = parse_document_text(sample_text)
        self.assertEqual(parsed['category'], 'driving_licence')
        self.assertEqual(parsed['document_number'], 'MH14 20180012345')
        self.assertEqual(parsed['issue_date'], '2018-06-05')
        self.assertEqual(parsed['expiry_date'], '2038-06-04')

    def test_date_normalization(self):
        self.assertEqual(normalize_date('25/12/2026'), '2026-12-25')
        self.assertEqual(normalize_date('2026-05-15'), '2026-05-15')
        self.assertEqual(normalize_date('10 Jan 2027'), '2027-01-10')
        self.assertIsNone(normalize_date('invalid date'))

    def test_ocr_availability_check_non_crashing(self):
        # Must return boolean without raising uncaught exceptions
        available = is_tesseract_available()
        self.assertIsInstance(available, bool)


if __name__ == '__main__':
    unittest.main()

