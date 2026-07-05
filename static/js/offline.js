// ============================================
// OFFLINE DATABASE - IndexedDB
// ============================================

class OfflineDB {
    constructor() {
        this.dbName = 'PrimeAccessDB';
        this.dbVersion = 1;
        this.db = null;
    }

    // Database initialize karein
    async init() {
        return new Promise((resolve, reject) => {
            const request = indexedDB.open(this.dbName, this.dbVersion);
            
            request.onupgradeneeded = (event) => {
                const db = event.target.result;
                
                // Tables create karein
                if (!db.objectStoreNames.contains('sales')) {
                    db.createObjectStore('sales', { keyPath: 'id', autoIncrement: true });
                }
                if (!db.objectStoreNames.contains('customers')) {
                    db.createObjectStore('customers', { keyPath: 'id', autoIncrement: true });
                }
                if (!db.objectStoreNames.contains('products')) {
                    db.createObjectStore('products', { keyPath: 'id', autoIncrement: true });
                }
                if (!db.objectStoreNames.contains('pending_sync')) {
                    db.createObjectStore('pending_sync', { keyPath: 'id', autoIncrement: true });
                }
            };

            request.onsuccess = (event) => {
                this.db = event.target.result;
                resolve(this.db);
            };

            request.onerror = (event) => {
                reject(event.target.error);
            };
        });
    }

    // Data save karein
    async saveData(storeName, data) {
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(storeName, 'readwrite');
            const store = transaction.objectStore(storeName);
            const request = store.add(data);
            
            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(request.error);
        });
    }

    // Data get karein
    async getData(storeName) {
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(storeName, 'readonly');
            const store = transaction.objectStore(storeName);
            const request = store.getAll();
            
            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(request.error);
        });
    }

    // Pending sync items save karein
    async savePendingSync(data) {
        return this.saveData('pending_sync', data);
    }

    // Sync pending items
    async syncPending() {
        const pending = await this.getData('pending_sync');
        
        for (const item of pending) {
            try {
                const response = await fetch('/api/sync', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(item)
                });
                
                if (response.ok) {
                    // Delete from pending
                    const transaction = this.db.transaction('pending_sync', 'readwrite');
                    const store = transaction.objectStore('pending_sync');
                    store.delete(item.id);
                }
            } catch (e) {
                console.log('Sync failed, will retry later');
            }
        }
    }
}

// Initialize
const offlineDB = new OfflineDB();
offlineDB.init();

// Auto sync when online
window.addEventListener('online', () => {
    offlineDB.syncPending();
});