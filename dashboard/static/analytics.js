// Analytics Dashboard
class AnalyticsDashboard {
    constructor() {
        this.charts = {};
        this.techBySeniorityData = {};
        this.init();
    }

    init() {
        this.loadAllData();
    }

    async loadAllData() {
        await Promise.all([
            this.loadQuickStats(),
            this.loadTechnologiesChart(),
            this.loadTimelineChart(),
            this.loadSeniorityChart(),
            this.loadContractChart(),
            this.loadRemoteChart(),
            this.loadCompaniesChart(),
            this.loadTechBySeniority(),
            this.loadTechCorrelation()
        ]);
    }

    async loadQuickStats() {
        try {
            const [statsRes, techRes, remoteRes, companiesRes] = await Promise.all([
                fetch('/api/stats'),
                fetch('/api/analytics/technologies'),
                fetch('/api/analytics/remote'),
                fetch('/api/analytics/top-companies?limit=1')
            ]);

            const stats = await statsRes.json();
            const tech = await techRes.json();
            const remote = await remoteRes.json();
            const companies = await companiesRes.json();

            // Update stats
            document.getElementById('total-techs').textContent = stats.unique_technologies;
            document.getElementById('top-tech').textContent = tech.labels[0] || 'N/A';
            
            const totalJobs = remote.remote + remote.onsite + remote.unknown;
            const remotePercent = totalJobs > 0 ? Math.round((remote.remote / totalJobs) * 100) : 0;
            document.getElementById('remote-percent').textContent = remotePercent + '%';
            
            document.getElementById('top-company').textContent = companies.companies[0] || 'N/A';
        } catch (error) {
            console.error('Error loading quick stats:', error);
        }
    }

    async loadTechnologiesChart() {
        try {
            const response = await fetch('/api/analytics/technologies');
            const data = await response.json();

            const ctx = document.getElementById('techChart').getContext('2d');
            this.charts.tech = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: data.labels,
                    datasets: [{
                        label: 'Nombre d\'offres',
                        data: data.data,
                        backgroundColor: 'rgba(233, 69, 96, 0.8)',
                        borderColor: 'rgba(233, 69, 96, 1)',
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: true,
                    plugins: {
                        legend: { display: false }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            ticks: { color: '#a0a0a0' },
                            grid: { color: '#2d2d44' }
                        },
                        x: {
                            ticks: { color: '#a0a0a0' },
                            grid: { display: false }
                        }
                    }
                }
            });
        } catch (error) {
            console.error('Error loading tech chart:', error);
        }
    }

    async loadTimelineChart() {
        try {
            const response = await fetch('/api/analytics/timeline?days=30');
            const data = await response.json();

            const ctx = document.getElementById('timelineChart').getContext('2d');
            this.charts.timeline = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: data.dates.map(d => d.slice(5)), // Remove year for readability
                    datasets: [{
                        label: 'Offres par jour',
                        data: data.counts,
                        borderColor: 'rgba(233, 69, 96, 1)',
                        backgroundColor: 'rgba(233, 69, 96, 0.1)',
                        fill: true,
                        tension: 0.4,
                        pointRadius: 3,
                        pointBackgroundColor: 'rgba(233, 69, 96, 1)'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: true,
                    plugins: {
                        legend: { display: false }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            ticks: { color: '#a0a0a0' },
                            grid: { color: '#2d2d44' }
                        },
                        x: {
                            ticks: { color: '#a0a0a0' },
                            grid: { display: false }
                        }
                    }
                }
            });
        } catch (error) {
            console.error('Error loading timeline chart:', error);
        }
    }

    async loadSeniorityChart() {
        try {
            const response = await fetch('/api/analytics/seniority');
            const data = await response.json();

            const colors = {
                'junior': 'rgba(46, 204, 113, 0.8)',
                'mid': 'rgba(52, 152, 219, 0.8)',
                'senior': 'rgba(155, 89, 182, 0.8)',
                'lead': 'rgba(231, 76, 60, 0.8)',
                'expert': 'rgba(241, 196, 15, 0.8)'
            };

            const ctx = document.getElementById('seniorityChart').getContext('2d');
            this.charts.seniority = new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: Object.keys(data).map(k => k.charAt(0).toUpperCase() + k.slice(1)),
                    datasets: [{
                        data: Object.values(data),
                        backgroundColor: Object.keys(data).map(k => colors[k] || 'rgba(149, 165, 166, 0.8)'),
                        borderWidth: 0
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: true,
                    plugins: {
                        legend: {
                            position: 'bottom',
                            labels: { color: '#a0a0a0' }
                        }
                    }
                }
            });
        } catch (error) {
            console.error('Error loading seniority chart:', error);
        }
    }

    async loadContractChart() {
        try {
            const response = await fetch('/api/analytics/contracts');
            const data = await response.json();

            const colors = {
                'cdi': 'rgba(46, 204, 113, 0.8)',
                'cdd': 'rgba(243, 156, 18, 0.8)',
                'freelance': 'rgba(155, 89, 182, 0.8)',
                'internship': 'rgba(52, 152, 219, 0.8)',
                'apprenticeship': 'rgba(26, 188, 156, 0.8)'
            };

            const ctx = document.getElementById('contractChart').getContext('2d');
            this.charts.contract = new Chart(ctx, {
                type: 'pie',
                data: {
                    labels: Object.keys(data).map(k => k.toUpperCase()),
                    datasets: [{
                        data: Object.values(data),
                        backgroundColor: Object.keys(data).map(k => colors[k] || 'rgba(149, 165, 166, 0.8)'),
                        borderWidth: 0
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: true,
                    plugins: {
                        legend: {
                            position: 'bottom',
                            labels: { color: '#a0a0a0' }
                        }
                    }
                }
            });
        } catch (error) {
            console.error('Error loading contract chart:', error);
        }
    }

    async loadRemoteChart() {
        try {
            const response = await fetch('/api/analytics/remote');
            const data = await response.json();

            const ctx = document.getElementById('remoteChart').getContext('2d');
            this.charts.remote = new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: ['Remote', 'Sur-site', 'Non spécifié'],
                    datasets: [{
                        data: [data.remote, data.onsite, data.unknown],
                        backgroundColor: [
                            'rgba(46, 204, 113, 0.8)',
                            'rgba(231, 76, 60, 0.8)',
                            'rgba(149, 165, 166, 0.8)'
                        ],
                        borderWidth: 0
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: true,
                    plugins: {
                        legend: {
                            position: 'bottom',
                            labels: { color: '#a0a0a0' }
                        }
                    }
                }
            });
        } catch (error) {
            console.error('Error loading remote chart:', error);
        }
    }

    async loadCompaniesChart() {
        try {
            const response = await fetch('/api/analytics/top-companies?limit=15');
            const data = await response.json();

            const ctx = document.getElementById('companiesChart').getContext('2d');
            this.charts.companies = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: data.companies,
                    datasets: [{
                        label: 'Nombre d\'offres',
                        data: data.counts,
                        backgroundColor: 'rgba(52, 152, 219, 0.8)',
                        borderColor: 'rgba(52, 152, 219, 1)',
                        borderWidth: 1
                    }]
                },
                options: {
                    indexAxis: 'y',
                    responsive: true,
                    maintainAspectRatio: true,
                    plugins: {
                        legend: { display: false }
                    },
                    scales: {
                        x: {
                            beginAtZero: true,
                            ticks: { color: '#a0a0a0' },
                            grid: { color: '#2d2d44' }
                        },
                        y: {
                            ticks: { color: '#a0a0a0' },
                            grid: { display: false }
                        }
                    }
                }
            });
        } catch (error) {
            console.error('Error loading companies chart:', error);
        }
    }

    async loadTechBySeniority() {
        try {
            const response = await fetch('/api/analytics/tech-by-seniority');
            this.techBySeniorityData = await response.json();
            
            // Show junior by default
            this.showTechBySeniority('junior');
        } catch (error) {
            console.error('Error loading tech by seniority:', error);
        }
    }

    showTechBySeniority(level) {
        const data = this.techBySeniorityData[level];
        if (!data) return;

        const labels = Object.keys(data);
        const values = Object.values(data);

        // Update button states
        document.querySelectorAll('.chart-controls .btn').forEach(btn => {
            btn.classList.remove('active');
        });
        event?.target?.classList.add('active');

        // Destroy existing chart if exists
        if (this.charts.techBySeniority) {
            this.charts.techBySeniority.destroy();
        }

        const ctx = document.getElementById('techBySeniorityChart').getContext('2d');
        this.charts.techBySeniority = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: `Technologies demandées (niveau ${level})`,
                    data: values,
                    backgroundColor: 'rgba(155, 89, 182, 0.8)',
                    borderColor: 'rgba(155, 89, 182, 1)',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: { color: '#a0a0a0' },
                        grid: { color: '#2d2d44' }
                    },
                    x: {
                        ticks: { color: '#a0a0a0' },
                        grid: { display: false }
                    }
                }
            }
        });
    }

    async loadTechCorrelation() {
        try {
            const response = await fetch('/api/analytics/tech-correlation');
            const data = await response.json();

            const container = document.getElementById('correlationTable');
            
            if (data.pairs.length === 0) {
                container.innerHTML = '<div class="loading-chart">Pas assez de données</div>';
                return;
            }

            container.innerHTML = `
                <div class="correlation-grid">
                    ${data.pairs.map(pair => `
                        <div class="correlation-item">
                            <div class="correlation-pair">
                                <span class="tech-badge">${pair.tech1}</span>
                                <span class="correlation-plus">+</span>
                                <span class="tech-badge">${pair.tech2}</span>
                            </div>
                            <span class="correlation-count">${pair.count}</span>
                        </div>
                    `).join('')}
                </div>
            `;
        } catch (error) {
            console.error('Error loading tech correlation:', error);
        }
    }
}

// Global function for button clicks
function showTechBySeniority(level) {
    analyticsDashboard.showTechBySeniority(level);
}

// Initialize
const analyticsDashboard = new AnalyticsDashboard();
