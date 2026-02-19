// Jobs Page App
class JobsPage {
    constructor() {
        this.currentPage = 1;
        this.perPage = 50;
        this.totalPages = 1;
        this.jobs = [];
        this.filters = {
            technologies: [],
            seniority: [],
            contract_type: [],
            remote_days: [],
            company: '',
            search: ''
        };
        this.init();
    }

    init() {
        this.loadFilterOptions();
        this.loadJobs();
        this.bindEvents();
    }

    bindEvents() {
        // Search input
        document.getElementById('search-input')?.addEventListener('input', (e) => {
            this.filters.search = e.target.value;
            this.debounce(this.applyFilters.bind(this), 300)();
        });

        // Company filter
        document.getElementById('company-filter')?.addEventListener('input', (e) => {
            this.filters.company = e.target.value;
            this.debounce(this.applyFilters.bind(this), 300)();
        });

        // Seniority checkboxes
        document.querySelectorAll('input[name="seniority"]').forEach(cb => {
            cb.addEventListener('change', () => this.updateSeniorityFilters());
        });

        // Contract checkboxes
        document.querySelectorAll('input[name="contract"]').forEach(cb => {
            cb.addEventListener('change', () => this.updateContractFilters());
        });

        // Remote checkboxes
        document.querySelectorAll('input[name="remote_days"]').forEach(cb => {
            cb.addEventListener('change', () => this.updateRemoteFilters());
        });

        // Per page selector
        document.getElementById('per-page')?.addEventListener('change', (e) => {
            this.perPage = parseInt(e.target.value);
            this.currentPage = 1;
            this.loadJobs();
        });

        // Apply filters button
        document.getElementById('apply-filters')?.addEventListener('click', () => {
            this.currentPage = 1;
            this.loadJobs();
        });

        // Reset filters button
        document.getElementById('reset-filters')?.addEventListener('click', () => {
            this.resetFilters();
        });

        // Pagination
        document.getElementById('prev-page')?.addEventListener('click', () => {
            if (this.currentPage > 1) {
                this.currentPage--;
                this.loadJobs();
            }
        });

        document.getElementById('next-page')?.addEventListener('click', () => {
            if (this.currentPage < this.totalPages) {
                this.currentPage++;
                this.loadJobs();
            }
        });
    }

    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    updateSeniorityFilters() {
        const checkboxes = document.querySelectorAll('input[name="seniority"]:checked');
        this.filters.seniority = Array.from(checkboxes).map(cb => cb.value);
        this.applyFilters();
    }

    updateContractFilters() {
        const checkboxes = document.querySelectorAll('input[name="contract"]:checked');
        this.filters.contract_type = Array.from(checkboxes).map(cb => cb.value);
        this.applyFilters();
    }

    updateRemoteFilters() {
        const checkboxes = document.querySelectorAll('input[name="remote_days"]:checked');
        this.filters.remote_days = Array.from(checkboxes).map(cb => cb.value);
        this.applyFilters();
    }

    applyFilters() {
        this.currentPage = 1;
        this.loadJobs();
    }

    resetFilters() {
        this.filters = {
            technologies: [],
            seniority: [],
            contract_type: [],
            remote_days: [],
            company: '',
            search: ''
        };
        this.currentPage = 1;

        // Reset UI
        document.getElementById('search-input').value = '';
        document.getElementById('company-filter').value = '';
        document.querySelectorAll('input[type="checkbox"]').forEach(cb => cb.checked = false);
        document.querySelectorAll('.tech-tag').forEach(tag => tag.classList.remove('selected'));

        this.loadJobs();
    }

    async loadFilterOptions() {
        try {
            const response = await fetch('/api/filters/options');
            const data = await response.json();
            this.renderTechFilters(data.technologies);
        } catch (error) {
            console.error('Error loading filter options:', error);
        }
    }

    renderTechFilters(technologies) {
        const container = document.getElementById('tech-filters');
        if (!container) return;

        if (technologies.length === 0) {
            container.innerHTML = '<div class="loading-small">Aucune technologie trouvée</div>';
            return;
        }

        container.innerHTML = technologies.map(tech => `
            <span class="tech-tag" data-tech="${tech}" onclick="jobsPage.toggleTech('${tech}')">${tech}</span>
        `).join('');
    }

    toggleTech(tech) {
        const index = this.filters.technologies.indexOf(tech);
        const tag = document.querySelector(`[data-tech="${tech}"]`);

        if (index === -1) {
            this.filters.technologies.push(tech);
            tag?.classList.add('selected');
        } else {
            this.filters.technologies.splice(index, 1);
            tag?.classList.remove('selected');
        }

        this.applyFilters();
    }

    async loadJobs() {
        try {
            const params = new URLSearchParams({
                page: this.currentPage,
                per_page: this.perPage
            });

            if (this.filters.search) params.append('search', this.filters.search);
            if (this.filters.company) params.append('company', this.filters.company);
            
            this.filters.technologies.forEach(t => params.append('technologies', t));
            this.filters.seniority.forEach(s => params.append('seniority', s));
            this.filters.contract_type.forEach(c => params.append('contract_type', c));
            this.filters.remote_days.forEach(r => params.append('remote_days', r));

            const response = await fetch(`/api/jobs?${params}`);
            const data = await response.json();

            this.jobs = data.jobs;
            this.totalPages = data.total_pages;
            this.currentPage = data.page;

            this.renderJobs();
            this.updatePagination();
            this.updateStats(data.total);
        } catch (error) {
            console.error('Error loading jobs:', error);
            document.getElementById('jobs-list').innerHTML = `
                <div class="loading">❌ Erreur lors du chargement des jobs</div>
            `;
        }
    }

    renderJobs() {
        const container = document.getElementById('jobs-list');
        
        if (this.jobs.length === 0) {
            container.innerHTML = `
                <div class="loading">
                    🔍 Aucun job trouvé avec ces filtres<br>
                    <small>Essayez de modifier vos critères de recherche</small>
                </div>
            `;
            return;
        }

        container.innerHTML = this.jobs.map((job, index) => {
            // Valeurs par défaut pour éviter les N/A
            const jobName = job.name && job.name !== 'N/A' && job.name !== 'Unknown Position' ? job.name : 'Poste non spécifié';
            const jobCompany = job.company && job.company !== 'N/A' && job.company !== 'Unknown Company' ? job.company : 'Entreprise non spécifiée';
            const jobLocation = job.location && job.location !== 'N/A' ? job.location : 'Paris';
            const jobLink = job.link || job.url || '#';
            const jobDate = job.date || 'Date inconnue';
            
            const techs = job.technologies?.slice(0, 8) || [];
            const moreTechs = (job.technologies?.length || 0) > 8 ? `+${job.technologies.length - 8}` : '';
            
            const seniority = job.seniority || 'not_specified';
            const contractType = job.contract_type || 'not_specified';
            const isRemote = job.remote || false;
            const remoteDays = job.remote_days;

            // Format remote label
            let remoteLabel = '';
            if (remoteDays === 'full') {
                remoteLabel = '🌍 Full Remote';
            } else if (typeof remoteDays === 'number') {
                remoteLabel = `🏠 ${remoteDays}j télétravail/semaine`;
            } else if (remoteDays === 'hybrid') {
                remoteLabel = '🏠 Télétravail hybride';
            } else if (isRemote) {
                remoteLabel = '🏠 Remote';
            }

            return `
            <div class="job-card">
                <div class="job-card-header">
                    <img src="${job.thumbnail || 'https://via.placeholder.com/50?text=JOB'}" 
                         alt="${jobCompany}" 
                         class="job-thumbnail"
                         onerror="this.src='https://via.placeholder.com/50?text=JOB'">
                    <div class="job-title-section">
                        <div class="job-title">${this.escapeHtml(jobName)}</div>
                        <div class="job-company">🏢 ${this.escapeHtml(jobCompany)}</div>
                        <div class="job-location">📍 ${this.escapeHtml(jobLocation)}</div>
                    </div>
                </div>

                <div class="job-meta">
                    ${seniority !== 'not_specified' ? `
                        <span class="job-tag seniority-${seniority}">
                            ${this.getSeniorityLabel(seniority)}
                        </span>
                    ` : ''}
                    ${contractType !== 'not_specified' ? `
                        <span class="job-tag contract-${contractType}">
                            ${contractType.toUpperCase()}
                        </span>
                    ` : ''}
                    ${remoteLabel ? `<span class="job-tag remote">${remoteLabel}</span>` : ''}
                </div>

                ${techs.length > 0 ? `
                    <div class="job-technologies">
                        ${techs.map(t => `<span class="tech-pill">${t}</span>`).join('')}
                        ${moreTechs ? `<span class="tech-pill">${moreTechs}</span>` : ''}
                    </div>
                ` : '<div class="job-technologies"><span class="tech-pill">Techno non détectée</span></div>'}

                <div class="job-actions">
                    <a href="${jobLink}" target="_blank" class="btn-job btn-view">
                        Voir l'offre →
                    </a>
                </div>
            </div>
        `}).join('');
    }

    getSeniorityLabel(level) {
        const labels = {
            'junior': 'Junior',
            'mid': 'Mid-level',
            'senior': 'Senior',
            'lead': 'Lead',
            'expert': 'Expert',
            'not_specified': 'Non spécifié'
        };
        return labels[level] || level;
    }

    updatePagination() {
        const prevBtn = document.getElementById('prev-page');
        const nextBtn = document.getElementById('next-page');
        const pageInfo = document.getElementById('page-info');

        if (prevBtn) prevBtn.disabled = this.currentPage <= 1;
        if (nextBtn) nextBtn.disabled = this.currentPage >= this.totalPages;
        if (pageInfo) pageInfo.textContent = `Page ${this.currentPage} / ${this.totalPages}`;
    }

    updateStats(total) {
        document.getElementById('results-count').textContent = `${total} job${total > 1 ? 's' : ''} trouvé${total > 1 ? 's' : ''}`;
    }

    escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Initialize
const jobsPage = new JobsPage();
