/**
 * Job Hunt Helper - Main JavaScript
 */

document.addEventListener('DOMContentLoaded', () => {
    // General helpers
    const showAlert = (message, type = 'success') => {
        // Implement a toast notification system here if needed
        alert(message);
    };

    // Scrape Jobs Button Handler
    const scrapeBtn = document.getElementById('scrapeBtn');
    if (scrapeBtn) {
        scrapeBtn.addEventListener('click', async (e) => {
            e.preventDefault();
            
            const modalElement = document.getElementById('scrapeModal');
            let modal = null;
            if (modalElement && typeof bootstrap !== 'undefined') {
                modal = new bootstrap.Modal(modalElement);
                modal.show();
            }

            const originalHTML = scrapeBtn.innerHTML;
            scrapeBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true"></span>Scraping...';
            scrapeBtn.disabled = true;

            const jobTypeSelect = document.getElementById('jobTypeSelect');
            const jobType = jobTypeSelect ? jobTypeSelect.value : 'permanent';

            try {
                const response = await fetch('/api/jobs/scrape', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ max_per_company: 3, job_type: jobType })
                });
                
                const data = await response.json();
                if (response.ok) {
                    showAlert(`Success: ${data.message || 'Scraped successfully'}`);
                    setTimeout(() => window.location.reload(), 1500);
                } else {
                    showAlert(`Error: ${data.detail || 'Failed to scrape jobs'}`, 'danger');
                }
            } catch (err) {
                showAlert('Failed to scrape jobs', 'danger');
            } finally {
                if (modal) {
                    modal.hide();
                }
                scrapeBtn.innerHTML = originalHTML;
                scrapeBtn.disabled = false;
            }
        });
    }

    // Resume Upload Handler
    const uploadForm = document.getElementById('uploadResumeForm');
    if (uploadForm) {
        uploadForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(uploadForm);
            const btn = uploadForm.querySelector('button');
            const originalText = btn.textContent;
            btn.textContent = 'Uploading...';
            btn.disabled = true;

            try {
                const response = await fetch('/api/resumes/', {
                    method: 'POST',
                    body: formData
                });
                if (response.ok) {
                    showAlert('Resume uploaded successfully!');
                    setTimeout(() => window.location.reload(), 1500);
                } else {
                    showAlert('Failed to upload resume', 'danger');
                }
            } catch (err) {
                showAlert('Error uploading resume', 'danger');
            } finally {
                btn.textContent = originalText;
                btn.disabled = false;
            }
        });
    }

    // Delete Job Handler
    document.addEventListener('click', async (e) => {
        const btn = e.target.closest('.delete-job-btn');
        if (btn) {
            if (!confirm('Are you sure you want to delete this job?')) return;
            const jobId = btn.dataset.jobId;
            btn.disabled = true;
            try {
                const response = await fetch(`/api/jobs/${jobId}`, {
                    method: 'DELETE'
                });
                if (response.ok) {
                    btn.closest('tr').remove();
                } else {
                    const errData = await response.json().catch(() => ({}));
                    showAlert(errData.detail || 'Failed to delete job', 'danger');
                    btn.disabled = false;
                }
            } catch (err) {
                showAlert('Error deleting job', 'danger');
                btn.disabled = false;
            }
        }
    });
});
