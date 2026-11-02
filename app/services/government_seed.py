"""Seed government certificate types and requirements."""
from app import create_app
from app.models import db, GovernmentCertificateType, GovernmentCertificateRequirement

app = create_app()

def seed_government_certificates():
    """Seed the government certificate catalog with predefined certificates."""

    certificates = [
        {
            'name': 'Domicile Certificate',
            'description': 'Proof of residence in a particular district. Required for various government applications, job applications, and educational purposes.',
            'portal_url': 'https://aaplesarkar.mahaonline.gov.in/',
            'portal_description': 'Maharashtra State Aadhaar Seva Portal',
            'processing_days_min': 3,
            'processing_days_max': 15,
            'is_active': True
        },
        {
            'name': 'Income Certificate',
            'description': 'Document certifying annual income for government schemes, scholarships, and subsidies. Issued by local Tahsildar office.',
            'portal_url': 'https://aaplesarkar.mahaonline.gov.in/',
            'portal_description': 'Maharashtra State Aadhaar Seva Portal',
            'processing_days_min': 2,
            'processing_days_max': 10,
            'is_active': True
        },
        {
            'name': 'Caste Certificate',
            'description': 'Certificate for members of Scheduled Castes, Scheduled Tribes, and Other Backward Classes eligible for reservation benefits.',
            'portal_url': 'https://aaplesarkar.mahaonline.gov.in/',
            'portal_description': 'Maharashtra State Aadhaar Seva Portal',
            'processing_days_min': 5,
            'processing_days_max': 20,
            'is_active': True
        },
        {
            'name': 'Non-Creamy Layer Certificate',
            'description': 'Certificate for OBC applicants to prove non-creamy layer status for government job applications and educational admissions.',
            'portal_url': 'https://aaplesarkar.mahaonline.gov.in/',
            'portal_description': 'Maharashtra State Aadhaar Seva Portal',
            'processing_days_min': 5,
            'processing_days_max': 25,
            'is_active': True
        },
        {
            'name': 'Marriage Certificate',
            'description': 'Legal proof of marriage. Required for joint applications, property transfers, and family benefits.',
            'portal_url': 'https://maharashtraonline.gov.in/',
            'portal_description': 'Maharashtra Online Services',
            'processing_days_min': 7,
            'processing_days_max': 30,
            'is_active': True
        },
        {
            'name': 'Property Document',
            'description': 'Land records, mutation documents, and property ownership proofs for government transactions.',
            'portal_url': 'https://maharashtra.gov.in/',
            'portal_description': 'Maharashtra Government Portal',
            'processing_days_min': 15,
            'processing_days_max': 60,
            'is_active': True
        },
        {
            'name': 'Birth Certificate',
            'description': 'Proof of birth for identity verification and age-related government benefits.',
            'portal_url': 'https://aaplesarkar.mahaonline.gov.in/',
            'portal_description': 'Maharashtra State Aadhaar Seva Portal',
            'processing_days_min': 7,
            'processing_days_max': 30,
            'is_active': True
        },
        {
            'name': 'Death Certificate',
            'description': 'Certified document for legal purposes, insurance claims, and government benefits.',
            'portal_url': 'https://maharashtraonline.gov.in/',
            'portal_description': 'Maharashtra Online Services',
            'processing_days_min': 5,
            'processing_days_max': 20,
            'is_active': True
        }
    ]

    with app.app_context():
        for cert_data in certificates:
            # Check if certificate already exists
            existing = GovernmentCertificateType.query.filter_by(name=cert_data['name']).first()
            if existing:
                print(f"Certificate type '{cert_data['name']}' already exists. Skipping.")
                continue

            # Create certificate type
            certificate = GovernmentCertificateType(
                name=cert_data['name'],
                description=cert_data['description'],
                portal_url=cert_data['portal_url'],
                portal_description=cert_data['portal_description'],
                processing_days_min=cert_data['processing_days_min'],
                processing_days_max=cert_data['processing_days_max'],
                is_active=cert_data['is_active']
            )
            db.session.add(certificate)
            db.session.flush()

            # Define requirements for each certificate type
            if cert_data['name'] == 'Domicile Certificate':
                requirements = [
                    {
                        'name': 'Application Form',
                        'description': 'Duly filled application form',
                        'document_type': 'pdf',
                        'is_mandatory': True,
                        'fee_amount': 0,
                        'order': 1
                    },
                    {
                        'name': 'Proof of Residence',
                        'description': 'Any one document showing current address (Electricity bill, Water bill, Ration card)',
                        'document_type': 'image',
                        'is_mandatory': True,
                        'fee_amount': 0,
                        'order': 2
                    },
                    {
                        'name': 'Identity Proof',
                        'description': 'Aadhaar Card, Passport, Driving License, or Voter ID',
                        'document_type': 'image',
                        'is_mandatory': True,
                        'fee_amount': 0,
                        'order': 3
                    },
                    {
                        'name': 'Passport Size Photo',
                        'description': 'Recent passport size photograph (white background)',
                        'document_type': 'image',
                        'is_mandatory': True,
                        'fee_amount': 0,
                        'order': 4
                    }
                ]
            elif cert_data['name'] == 'Income Certificate':
                requirements = [
                    {
                        'name': 'Application Form',
                        'description': 'Duly filled application form',
                        'document_type': 'pdf',
                        'is_mandatory': True,
                        'fee_amount': 0,
                        'order': 1
                    },
                    {
                        'name': 'Proof of Income',
                        'description': 'Salary slips (last 3 months), Income Tax Return, or Business Income Documents',
                        'document_type': 'pdf',
                        'is_mandatory': True,
                        'fee_amount': 0,
                        'order': 2
                    },
                    {
                        'name': 'Identity Proof',
                        'description': 'Aadhaar Card, Passport, Driving License, or Voter ID',
                        'document_type': 'image',
                        'is_mandatory': True,
                        'fee_amount': 0,
                        'order': 3
                    },
                    {
                        'name': 'Passport Size Photo',
                        'description': 'Recent passport size photograph',
                        'document_type': 'image',
                        'is_mandatory': True,
                        'fee_amount': 0,
                        'order': 4
                    }
                ]
            elif cert_data['name'] == 'Caste Certificate':
                requirements = [
                    {
                        'name': 'Application Form',
                        'description': 'Duly filled application form',
                        'document_type': 'pdf',
                        'is_mandatory': True,
                        'fee_amount': 0,
                        'order': 1
                    },
                    {
                        'name': 'Caste Proof',
                        'description': 'Previous caste certificate or community certificate',
                        'document_type': 'pdf',
                        'is_mandatory': True,
                        'fee_amount': 0,
                        'order': 2
                    },
                    {
                        'name': 'Identity Proof',
                        'description': 'Aadhaar Card, Passport, Driving License, or Voter ID',
                        'document_type': 'image',
                        'is_mandatory': True,
                        'fee_amount': 0,
                        'order': 3
                    },
                    {
                        'name': 'Birth Certificate',
                        'description': 'Proof of birth (Birth certificate or SSLC certificate)',
                        'document_type': 'pdf',
                        'is_mandatory': True,
                        'fee_amount': 0,
                        'order': 4
                    },
                    {
                        'name': 'Passport Size Photo',
                        'description': 'Recent passport size photograph',
                        'document_type': 'image',
                        'is_mandatory': True,
                        'fee_amount': 0,
                        'order': 5
                    }
                ]
            elif cert_data['name'] == 'Non-Creamy Layer Certificate':
                requirements = [
                    {
                        'name': 'Application Form',
                        'description': 'Duly filled application form',
                        'document_type': 'pdf',
                        'is_mandatory': True,
                        'fee_amount': 0,
                        'order': 1
                    },
                    {
                        'name': 'Income Proof',
                        'description': 'Income tax returns, salary slips, or business income proof (last financial year)',
                        'document_type': 'pdf',
                        'is_mandatory': True,
                        'fee_amount': 0,
                        'order': 2
                    },
                    {
                        'name': 'Caste Certificate',
                        'description': 'Existing valid caste certificate',
                        'document_type': 'pdf',
                        'is_mandatory': True,
                        'fee_amount': 0,
                        'order': 3
                    },
                    {
                        'name': 'Identity Proof',
                        'description': 'Aadhaar Card, Passport, Driving License, or Voter ID',
                        'document_type': 'image',
                        'is_mandatory': True,
                        'fee_amount': 0,
                        'order': 4
                    },
                    {
                        'name': 'Passport Size Photo',
                        'description': 'Recent passport size photograph',
                        'document_type': 'image',
                        'is_mandatory': True,
                        'fee_amount': 0,
                        'order': 5
                    }
                ]
            else:
                # Default requirements for other certificates
                requirements = [
                    {
                        'name': 'Application Form',
                        'description': 'Duly filled application form',
                        'document_type': 'pdf',
                        'is_mandatory': True,
                        'fee_amount': 0,
                        'order': 1
                    },
                    {
                        'name': 'Identity Proof',
                        'description': 'Aadhaar Card, Passport, Driving License, or Voter ID',
                        'document_type': 'image',
                        'is_mandatory': True,
                        'fee_amount': 0,
                        'order': 2
                    },
                    {
                        'name': 'Passport Size Photo',
                        'description': 'Recent passport size photograph',
                        'document_type': 'image',
                        'is_mandatory': True,
                        'fee_amount': 0,
                        'order': 3
                    }
                ]

            # Add requirements
            for req_data in requirements:
                requirement = GovernmentCertificateRequirement(
                    certificate_type_id=certificate.id,
                    name=req_data['name'],
                    description=req_data['description'],
                    document_type=req_data['document_type'],
                    is_mandatory=req_data['is_mandatory'],
                    fee_amount=req_data['fee_amount'],
                    order=req_data['order']
                )
                db.session.add(requirement)

            db.session.commit()
            print(f"Seeded certificate: {cert_data['name']} with {len(requirements)} requirements")

        print(" Government certificate seeding complete!")


if __name__ == '__main__':
    seed_government_certificates()