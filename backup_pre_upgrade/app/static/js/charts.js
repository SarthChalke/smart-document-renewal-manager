// ═══════════════════════════════════════════
// Dashboard Charts — Premium Design (Chart.js)
// ═══════════════════════════════════════════

document.addEventListener('DOMContentLoaded', function() {
    // Set global Chart.js defaults
    Chart.defaults.font.family = "'Inter', sans-serif";
    Chart.defaults.font.size = 11;
    Chart.defaults.color = '#64748b';
    Chart.defaults.plugins.tooltip.backgroundColor = '#0f172a';
    Chart.defaults.plugins.tooltip.titleFont = { weight: '600', size: 12 };
    Chart.defaults.plugins.tooltip.bodyFont = { size: 11 };
    Chart.defaults.plugins.tooltip.cornerRadius = 8;
    Chart.defaults.plugins.tooltip.padding = { top: 10, bottom: 10, left: 14, right: 14 };
    Chart.defaults.plugins.tooltip.displayColors = true;
    Chart.defaults.plugins.tooltip.boxPadding = 4;

    fetch('/api/chart-data')
        .then(response => response.json())
        .then(data => {
            renderDocCategoryChart(data.doc_categories);
            renderDocStatusChart(data.doc_status);
            renderLoanDistChart(data.loan_distribution);
            renderMonthlyPaymentsChart(data.monthly_payments);
            renderPaidVsPendingChart(data.paid_vs_pending);
        })
        .catch(err => console.error('Chart data error:', err));
});

// Curated palette with excellent contrast
const chartPalette = [
    '#2563eb', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6',
    '#06b6d4', '#ec4899', '#f97316', '#14b8a6', '#6366f1'
];

// Semi-transparent variants for fills
const chartPaletteAlpha = chartPalette.map(c => c + '20');

const legendConfig = {
    position: 'bottom',
    labels: {
        padding: 18,
        usePointStyle: true,
        pointStyle: 'circle',
        font: { size: 11, family: "'Inter', sans-serif", weight: '500' }
    }
};

function hasData(obj) {
    return obj && Object.keys(obj).length > 0 && Object.values(obj).some(v => v > 0);
}

function showEmpty(chartId, emptyId) {
    const canvas = document.getElementById(chartId);
    const empty = document.getElementById(emptyId);
    if (canvas) canvas.style.display = 'none';
    if (empty) empty.style.display = 'flex';
}


function renderDocCategoryChart(data) {
    const ctx = document.getElementById('docCategoryChart');
    if (!ctx) return;
    if (!hasData(data)) { showEmpty('docCategoryChart', 'docCategoryEmpty'); return; }

    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: Object.keys(data),
            datasets: [{
                data: Object.values(data),
                backgroundColor: chartPalette,
                borderWidth: 3,
                borderColor: '#ffffff',
                hoverOffset: 8,
                hoverBorderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: legendConfig,
                tooltip: {
                    callbacks: {
                        label: function(ctx) {
                            const total = ctx.dataset.data.reduce((a, b) => a + b, 0);
                            const pct = total > 0 ? ((ctx.raw / total) * 100).toFixed(1) : 0;
                            return ` ${ctx.label}: ${ctx.raw} (${pct}%)`;
                        }
                    }
                }
            },
            cutout: '68%',
            animation: { animateRotate: true, duration: 800 }
        }
    });
}

function renderDocStatusChart(data) {
    const ctx = document.getElementById('docStatusChart');
    if (!ctx) return;

    const statusColors = {
        'Valid': '#10b981',
        'Expiring Soon': '#f59e0b',
        'Expired': '#ef4444',
        'No Expiry': '#94a3b8'
    };

    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: Object.keys(data),
            datasets: [{
                data: Object.values(data),
                backgroundColor: Object.keys(data).map(k => statusColors[k] || '#94a3b8'),
                borderWidth: 3,
                borderColor: '#ffffff',
                hoverOffset: 8,
                hoverBorderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: legendConfig,
                tooltip: {
                    callbacks: {
                        label: function(ctx) {
                            const total = ctx.dataset.data.reduce((a, b) => a + b, 0);
                            const pct = total > 0 ? ((ctx.raw / total) * 100).toFixed(1) : 0;
                            return ` ${ctx.label}: ${ctx.raw} (${pct}%)`;
                        }
                    }
                }
            },
            cutout: '68%',
            animation: { animateRotate: true, duration: 800 }
        }
    });
}

function renderLoanDistChart(data) {
    const ctx = document.getElementById('loanDistChart');
    if (!ctx) return;
    if (!hasData(data)) { showEmpty('loanDistChart', 'loanDistEmpty'); return; }

    const gradient = ctx.getContext('2d');
    const grad = gradient.createLinearGradient(0, 0, 0, 280);
    grad.addColorStop(0, '#2563eb');
    grad.addColorStop(1, '#3b82f6');

    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: Object.keys(data),
            datasets: [{
                label: 'Loans',
                data: Object.values(data),
                backgroundColor: grad,
                borderRadius: 8,
                borderSkipped: false,
                barThickness: 'flex',
                maxBarThickness: 48,
                hoverBackgroundColor: '#1d4ed8'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        stepSize: 1,
                        font: { size: 11, family: "'Inter'" },
                        color: '#94a3b8'
                    },
                    grid: { color: 'rgba(226,232,240,0.6)', drawBorder: false }
                },
                x: {
                    ticks: {
                        font: { size: 10, family: "'Inter'", weight: '500' },
                        color: '#64748b'
                    },
                    grid: { display: false }
                }
            },
            animation: { duration: 1000 }
        }
    });
}

function renderMonthlyPaymentsChart(data) {
    const ctx = document.getElementById('monthlyPaymentsChart');
    if (!ctx) return;
    if (!hasData(data)) { showEmpty('monthlyPaymentsChart', 'monthlyPaymentsEmpty'); return; }

    const gradient = ctx.getContext('2d');
    const fill = gradient.createLinearGradient(0, 0, 0, 280);
    fill.addColorStop(0, 'rgba(37, 99, 235, 0.15)');
    fill.addColorStop(1, 'rgba(37, 99, 235, 0.01)');

    new Chart(ctx, {
        type: 'line',
        data: {
            labels: Object.keys(data),
            datasets: [{
                label: 'Payments',
                data: Object.values(data),
                borderColor: '#2563eb',
                backgroundColor: fill,
                fill: true,
                tension: 0.4,
                pointRadius: 6,
                pointBackgroundColor: '#2563eb',
                pointBorderColor: '#ffffff',
                pointBorderWidth: 3,
                pointHoverRadius: 8,
                pointHoverBorderWidth: 3,
                pointHoverBackgroundColor: '#1d4ed8',
                borderWidth: 2.5,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        stepSize: 1,
                        font: { size: 11, family: "'Inter'" },
                        color: '#94a3b8'
                    },
                    grid: { color: 'rgba(226,232,240,0.6)', drawBorder: false }
                },
                x: {
                    ticks: {
                        font: { size: 10, family: "'Inter'", weight: '500' },
                        color: '#64748b'
                    },
                    grid: { display: false }
                }
            },
            interaction: { mode: 'index', intersect: false },
            animation: { duration: 1200 }
        }
    });
}

function renderPaidVsPendingChart(data) {
    const ctx = document.getElementById('paidPendingChart');
    if (!ctx) return;

    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: Object.keys(data),
            datasets: [{
                data: Object.values(data),
                backgroundColor: ['#10b981', '#f59e0b'],
                borderWidth: 3,
                borderColor: '#ffffff',
                hoverOffset: 8,
                hoverBorderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: legendConfig,
                tooltip: {
                    callbacks: {
                        label: function(ctx) {
                            const total = ctx.dataset.data.reduce((a, b) => a + b, 0);
                            const pct = total > 0 ? ((ctx.raw / total) * 100).toFixed(1) : 0;
                            return ` ${ctx.label}: ${ctx.raw} (${pct}%)`;
                        }
                    }
                }
            },
            cutout: '68%',
            animation: { animateRotate: true, duration: 800 }
        }
    });
}
