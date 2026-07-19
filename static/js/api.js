/**
 * app/static/js/api.js
 * Flask API fetch wrapper layer — abstracts backend endpoints
 * Replaces all hardcoded mock data with live server calls
 */

class RoadPulseAPI {
    constructor(baseUrl = '') {
        this.baseUrl = baseUrl || window.location.origin;
    }

    /**
     * POST /api/report
     * Submit incident report with image, location, GPS, and notes
     */
    async submitIncidentReport(formData) {
        try {
            const response = await fetch(`${this.baseUrl}/api/report`, {
                method: 'POST',
                body: formData
            });
            return await response.json();
        } catch (error) {
            console.error('Report submission failed:', error);
            return { success: false, error: error.message };
        }
    }

    /**
     * GET /api/incidents
     * Fetch all active incidents, optionally filtered
     */
    async getIncidents(filters = {}) {
        const params = new URLSearchParams(filters);
        try {
            const response = await fetch(`${this.baseUrl}/api/incidents?${params}`, {
                method: 'GET'
            });
            return await response.json();
        } catch (error) {
            console.error('Failed to fetch incidents:', error);
            return { success: false, incidents: [], error: error.message };
        }
    }

    /**
     * GET /api/stats
     * Fetch aggregated incident statistics
     */
    async getStats() {
        try {
            const response = await fetch(`${this.baseUrl}/api/stats`, {
                method: 'GET'
            });
            return await response.json();
        } catch (error) {
            console.error('Failed to fetch stats:', error);
            return { success: false, stats: {}, error: error.message };
        }
    }

    /**
     * POST /smart-route
     * Calculate safe routing around hazards using Gemini geocoding + TomTom
     */
    async fetchSmartRoute(startText, endText) {
        try {
            const response = await fetch(`${this.baseUrl}/smart-route`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    start_text: startText,
                    end_text: endText
                })
            });
            return await response.json();
        } catch (error) {
            console.error('Smart route calculation failed:', error);
            return { error: error.message };
        }
    }
    /**
     * GET /api/analytics
     * Fetch dashboard metrics like resolution time and ward quality
     */
    async fetchAnalytics() {
        try {
            const response = await fetch(`${this.baseUrl}/api/analytics`, {
                method: 'GET'
            });
            return await response.json();
        } catch (error) {
            console.error('Failed to fetch analytics:', error);
            return { success: false, metrics: {}, error: error.message };
        }
    }
}

// Global API instance
const API = new RoadPulseAPI();
