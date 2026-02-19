// Dashboard App
class Dashboard {
    constructor() {
        this.refreshInterval = 5000; // 5 secondes
        this.init();
    }

    init() {
        this.loadStats();
        this.loadJobs();
        this.loadLogs();
        
        // Auto-refresh
        setInterval(() => {
            this.loadStats();
            this.loadJobs();
            this.loadLogs();
        }, this.refreshInterval);
    }

    // Load stats
    async loadStats() {
        try {
            const response = await fetch('/api/stats');
            const data = await response.json();
            
            document.getElementById('total-jobs').textContent = data.total_jobs;
            document.getElementById('jobs-24h').textContent = data.jobs_24h;
            document.getElementById('last-update').textContent = data.last_update;
        } catch (error) {
            console.error('Error loading stats:', error);
        }
    }

    // Load jobs
    async loadJobs() {
        try {
            const response = await fetch('/api/jobs');
            const jobs = await response.json();
            
            const container = document.getElementById('jobs-list');
            
            if (jobs.length === 0) {
                container.innerHTML = '<div class="loading">Aucun job trouvé</div>';
                return;
            }
            
            container.innerHTML = jobs.map(job => `
                <div class="job-item">
                    <div class="job-title">${this.escapeHtml(job.name)}</div>
                    <div class="job-company">🏢 ${this.escapeHtml(job.company)}</div>
                    <div class="job-location">📍 ${this.escapeHtml(job.location)}</div>
                    <div class="job-date">🕐 ${job.date}</div>
                    <a href="${job.link}" target="_blank" class="job-link">Voir l'offre →</a>
                </div>
            `).join('');
        } catch (error) {
            console.error('Error loading jobs:', error);
        }
    }

    // Load logs
    async loadLogs() {
        try {
            const response = await fetch('/api/logs');
            const logs = await response.json();
            
            const container = document.getElementById('logs-container');
            
            if (logs.length === 0) {
                container.innerHTML = '<div class="loading">Aucun log</div>';
                return;
            }
            
            container.innerHTML = logs.map(log => `
                <div class="log-entry ${log.level.toLowerCase()}">
                    <span class="log-time">${log.timestamp.split(' ')[1]}</span>
                    <span class="log-level ${log.level.toLowerCase()}">${log.level}</span>
                    <span class="log-message">${this.escapeHtml(log.message)}</span>
                    ${log.website ? `<span class="log-website">${this.escapeHtml(log.website)}</span>` : ''}
                </div>
            `).join('');
            
            // Scroll to top
            container.scrollTop = 0;
        } catch (error) {
            console.error('Error loading logs:', error);
        }
    }

    // Escape HTML to prevent XSS
    escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new Dashboard();
});
