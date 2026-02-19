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
            const response = await fetch('/api/jobs?per_page=10');
            const data = await response.json();
            const jobs = data.jobs || [];
            
            const container = document.getElementById('jobs-list');
            
            if (jobs.length === 0) {
                container.innerHTML = '<div class="loading">Aucun job trouvé</div>';
                return;
            }
            
            container.innerHTML = jobs.map((job, index) => {
                // Valeurs par défaut
                const jobName = job.name && job.name !== 'N/A' ? job.name : 'Poste non spécifié';
                const jobCompany = job.company && job.company !== 'N/A' ? job.company : 'Entreprise non spécifiée';
                const jobLocation = job.location && job.location !== 'N/A' ? job.location : 'Paris';
                const jobLink = job.link || job.url || '#';
                const jobDate = job.date || 'Date inconnue';
                
                return `
                <div class="job-item" onclick="window.open('${jobLink}', '_blank')" title="Cliquez pour voir l'offre">
                    <div class="job-title">${this.escapeHtml(jobName)}</div>
                    <div class="job-company">🏢 ${this.escapeHtml(jobCompany)}</div>
                    <div class="job-location">📍 ${this.escapeHtml(jobLocation)}</div>
                    <div class="job-date">🕐 ${jobDate}</div>
                    <a href="${jobLink}" target="_blank" class="job-link" onclick="event.stopPropagation()">Voir l'offre →</a>
                </div>
            `}).join('');
            
            // Add click handlers
            document.querySelectorAll('.job-item').forEach((item, index) => {
                item.style.cursor = 'pointer';
            });
        } catch (error) {
            console.error('Error loading jobs:', error);
            document.getElementById('jobs-list').innerHTML = '<div class="loading">Erreur de chargement</div>';
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
