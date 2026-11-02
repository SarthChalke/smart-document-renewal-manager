"""Search routes."""
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import Document, User, Loan

search_bp = Blueprint('search', __name__, url_prefix='/search')


@search_bp.route('/')
@login_required
def search():
    query = request.args.get('q', '').strip()
    search_type = request.args.get('type', 'all').strip()

    results = {'documents': [], 'users': [], 'loans': []}

    if not query:
        return render_template('search.html', results=results)

    # Search documents
    if search_type in ['all', 'documents']:
        doc_results = Document.query.filter_by(user_id=current_user.id).filter(
            (Document.title.ilike(f'%{query}%')) |
            (Document.document_number.ilike(f'%{query}%')) |
            (Document.holder_name.ilike(f'%{query}%')) |
            (Document.issuing_authority.ilike(f'%{query}%'))
        ).limit(10).all()
        results['documents'] = doc_results

    # Search loans
    if search_type in ['all', 'loans']:
        loan_results = Loan.query.filter_by(user_id=current_user.id).filter(
            (Loan.loan_type.ilike(f'%{query}%')) |
            (str(Loan.id).ilike(f'%{query}%'))
        ).limit(10).all()
        results['loans'] = loan_results

    return render_template('search.html', results=results, query=query, search_type=search_type)


@search_bp.route('/ajax')
@login_required
def search_ajax():
    query = request.args.get('q', '').strip()
    search_type = request.args.get('type', 'all').strip()

    results = {'documents': [], 'users': [], 'loans': []}

    if not query:
        return jsonify(results)

    # Search documents
    if search_type in ['all', 'documents']:
        doc_results = Document.query.filter_by(user_id=current_user.id).filter(
            (Document.title.ilike(f'%{query}%')) |
            (Document.document_number.ilike(f'%{query}%')) |
            (Document.holder_name.ilike(f'%{query}%')) |
            (Document.issuing_authority.ilike(f'%{query}%'))
        ).limit(10).all()
        results['documents'] = [
            {
                'id': doc.id,
                'title': doc.title,
                'category': doc.category,
                'document_number': doc.document_number,
                'holder_name': doc.holder_name,
                'expiry_date': doc.expiry_date.strftime('%Y-%m-%d') if doc.expiry_date else None,
                'type': 'document'
            }
            for doc in doc_results
        ]

    # Search loans
    if search_type in ['all', 'loans']:
        loan_results = Loan.query.filter_by(user_id=current_user.id).filter(
            (Loan.loan_type.ilike(f'%{query}%')) |
            (str(Loan.id).ilike(f'%{query}%'))
        ).limit(10).all()
        results['loans'] = [
            {
                'id': loan.id,
                'loan_type': loan.loan_type,
                'principal_amount': float(loan.principal_amount),
                'monthly_emi': float(loan.monthly_emi) if loan.monthly_emi else None,
                'status': loan.status,
                'type': 'loan'
            }
            for loan in loan_results
        ]

    return jsonify(results)