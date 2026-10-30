// ==============================================================================
// Chart.js Visualizations for Dashboard and EMI Calculator
// Vibrant Color Palette (STRICT CONSTRAINT: ZERO GREEN)
// Palette: Royal Purple (#6C3BFF), Cyan (#22C7D6), Electric Blue (#2878FF),
// Vibrant Pink (#F044A7), Orange (#FF9F43), Yellow (#FFD166), Coral (#FF6B6B)
// ==============================================================================

document.addEventListener('DOMContentLoaded', function () {
    // ── 1. Dashboard Charts ───────────────────────────────────
    const docOverviewCanvas = document.getElementById('docOverviewChart');
    const loanStatusCanvas = document.getElementById('loanStatusChart');
    const monthlyPaymentsCanvas = document.getElementById('monthlyPaymentsChart');
    const principalVsInterestCanvas = document.getElementById('principalVsInterestChart');

    if (docOverviewCanvas || loanStatusCanvas || monthlyPaymentsCanvas) {
        fetch('/api/dashboard-charts')
            .then(res => res.json())
            .then(data => {
                // Document Overview Donut: Valid (Cyan), Expiring (Orange), Expired (Coral), Renewed (Electric Blue), Today (Yellow)
                if (docOverviewCanvas && data.doc_status) {
                    new Chart(docOverviewCanvas, {
                        type: 'doughnut',
                        data: {
                            labels: Object.keys(data.doc_status),
                            datasets: [{
                                data: Object.values(data.doc_status),
                                backgroundColor: ['#22C7D6', '#FF9F43', '#FF6B6B', '#2878FF', '#6C3BFF', '#F044A7'],
                                borderWidth: 2,
                                borderColor: '#ffffff'
                            }]
                        },
                        options: {
                            responsive: true,
                            plugins: {
                                legend: { position: 'bottom', labels: { boxWidth: 12, font: { size: 11, weight: '600' } } }
                            },
                            cutout: '65%'
                        }
                    });
                }

                // Monthly Payments Bar Chart: Vibrant Royal Purple Gradient
                if (monthlyPaymentsCanvas && data.monthly_payments) {
                    new Chart(monthlyPaymentsCanvas, {
                        type: 'bar',
                        data: {
                            labels: Object.keys(data.monthly_payments),
                            datasets: [{
                                label: 'Amount Paid (₹)',
                                data: Object.values(data.monthly_payments),
                                backgroundColor: '#6C3BFF',
                                hoverBackgroundColor: '#5125D4',
                                borderRadius: 8
                            }]
                        },
                        options: {
                            responsive: true,
                            plugins: {
                                legend: { display: false }
                            },
                            scales: {
                                y: {
                                    beginAtZero: true,
                                    grid: { color: '#E4E1F5' },
                                    ticks: {
                                        callback: function(val) { return '₹' + val.toLocaleString('en-IN'); },
                                        font: { size: 10 }
                                    }
                                },
                                x: {
                                    grid: { display: false },
                                    ticks: { font: { size: 10 } }
                                }
                            }
                        }
                    });
                }

                // Loan Status Pie: Active (Royal Purple), Closed (Electric Blue), Overdue (Coral), Pending (Orange)
                if (loanStatusCanvas && data.loan_status) {
                    new Chart(loanStatusCanvas, {
                        type: 'pie',
                        data: {
                            labels: Object.keys(data.loan_status),
                            datasets: [{
                                data: Object.values(data.loan_status),
                                backgroundColor: ['#6C3BFF', '#2878FF', '#FF6B6B', '#FF9F43', '#22C7D6'],
                                borderWidth: 2,
                                borderColor: '#ffffff'
                            }]
                        },
                        options: {
                            responsive: true,
                            plugins: {
                                legend: { position: 'bottom', labels: { boxWidth: 12, font: { size: 11, weight: '600' } } }
                            }
                        }
                    });
                }

                // Principal vs Interest Donut: Principal (Royal Purple), Interest (Vibrant Pink / Coral)
                if (principalVsInterestCanvas && data.principal_vs_interest) {
                    new Chart(principalVsInterestCanvas, {
                        type: 'doughnut',
                        data: {
                            labels: ['Total Principal', 'Total Interest'],
                            datasets: [{
                                data: [data.principal_vs_interest.Principal, data.principal_vs_interest['Total Interest']],
                                backgroundColor: ['#6C3BFF', '#F044A7'],
                                borderWidth: 2,
                                borderColor: '#ffffff'
                            }]
                        },
                        options: {
                            responsive: true,
                            plugins: {
                                legend: { position: 'bottom', labels: { boxWidth: 12, font: { size: 11, weight: '600' } } }
                            },
                            cutout: '65%'
                        }
                    });
                }
            })
            .catch(err => console.error("Error loading dashboard charts:", err));
    }

    // ── 2. EMI Calculator Chart: Principal (Royal Purple), Interest (Vibrant Pink) ──
    const emiCalcCanvas = document.getElementById('emiCalculatorChart');
    if (emiCalcCanvas && window.calculatorData) {
        new Chart(emiCalcCanvas, {
            type: 'doughnut',
            data: {
                labels: ['Principal Amount', 'Total Interest'],
                datasets: [{
                    data: [window.calculatorData.principal, window.calculatorData.interest],
                    backgroundColor: ['#6C3BFF', '#F044A7'],
                    borderWidth: 3,
                    borderColor: '#ffffff'
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { position: 'bottom', labels: { font: { size: 12, weight: '600' } } },
                    tooltip: {
                        callbacks: {
                            label: function(ctx) {
                                return ctx.label + ': ₹' + Number(ctx.raw).toLocaleString('en-IN', { minimumFractionDigits: 2 });
                            }
                        }
                    }
                },
                cutout: '60%'
            }
        });
    }
});
