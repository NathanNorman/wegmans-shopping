let cart = [];
const NC_TAX_RATE = 0.04;

// Favorites state
let userFavorites = new Set(); // Set of favorited product names

// Search pagination state
let currentSearchTerm = '';
let currentSearchResults = [];
const RESULTS_PER_PAGE = 20;

// Store selection
let selectedStore = localStorage.getItem('selectedStore') || '86'; // Default: Raleigh

// Verified Wegmans stores (only stores with Algolia product data)
// Total: 88 stores across 7 states
// Note: Verified against Algolia API - all stores guaranteed to have product search
const WEGMANS_STORES = {
    'NY': [
        {number: 1, name: 'Buffalo - Amherst St'},
        {number: 4, name: 'Rochester - East Ave'},
        {number: 11, name: 'Syracuse - James St'},
        {number: 13, name: 'Rochester - Lyell Ave'},
        {number: 14, name: 'Buffalo - Dick Road'},
        {number: 20, name: 'Rochester - Calkins Road'},
        {number: 24, name: 'Rochester - Marketplace'},
        {number: 26, name: 'Rochester - Hudson Ave'},
        {number: 34, name: 'Canandaigua'},
        {number: 38, name: 'Syracuse - Clay'},
        {number: 41, name: 'Corning'},
        {number: 46, name: 'Auburn'},
        {number: 48, name: 'Olean'},
        {number: 50, name: 'Binghamton'},
        {number: 54, name: 'Rochester - Perinton'},
        {number: 56, name: 'Rochester - Gates'},
        {number: 57, name: 'Rochester - Penfield'},
        {number: 62, name: 'Saratoga Springs'},
        {number: 68, name: 'Rochester - College Town'},
        {number: 76, name: 'Elmira'},
        {number: 77, name: 'Webster'},
        {number: 78, name: 'Oswego'},
        {number: 80, name: 'Batavia'},
        {number: 84, name: 'Amherst'},
        {number: 92, name: 'Geneva'},
        {number: 93, name: 'Brockport'},
        {number: 95, name: 'Cicero'},
        {number: 97, name: 'Rome'},
        {number: 104, name: 'Victor'},
        {number: 105, name: 'New Hartford'},
        {number: 108, name: 'Geneseo'},
        {number: 111, name: 'Henrietta'},
        {number: 115, name: 'Brooklyn'}
    ],
    'PA': [
        {number: 3, name: 'Wilkes-Barre'},
        {number: 16, name: 'State College'},
        {number: 22, name: 'Scranton'},
        {number: 30, name: 'Dickson City'},
        {number: 59, name: 'Easton'},
        {number: 60, name: 'Bethlehem'},
        {number: 66, name: 'Allentown'},
        {number: 67, name: 'Langhorne'},
        {number: 75, name: 'Downingtown'},
        {number: 79, name: 'Warrington'},
        {number: 82, name: 'East Stroudsburg'},
        {number: 87, name: 'Hanover Township'},
        {number: 88, name: 'State College - Colonnade'},
        {number: 89, name: 'Hazleton'},
        {number: 94, name: 'Boalsburg'},
        {number: 96, name: 'Mechanicsburg'},
        {number: 98, name: 'Collegeville'}
    ],
    'NJ': [
        {number: 7, name: 'Bridgewater'},
        {number: 8, name: 'Woodbridge'},
        {number: 9, name: 'Princeton'},
        {number: 18, name: 'Manalapan'},
        {number: 19, name: 'Cherry Hill'},
        {number: 31, name: 'Mt. Laurel'},
        {number: 37, name: 'Ocean'},
        {number: 40, name: 'Hanover'},
        {number: 51, name: 'Marlton'},
        {number: 55, name: 'Montgomery'},
        {number: 64, name: 'Manalapan - 2'},
        {number: 71, name: 'Montvale'}
    ],
    'VA': [
        {number: 44, name: 'Charlottesville - Hydraulic'},
        {number: 47, name: 'Fredericksburg'},
        {number: 49, name: 'Sterling'},
        {number: 58, name: 'Leesburg'},
        {number: 63, name: 'Short Pump'},
        {number: 65, name: 'Woodbridge'},
        {number: 69, name: 'Fairfax'},
        {number: 70, name: 'Midlothian'},
        {number: 73, name: 'Fair Lakes'},
        {number: 83, name: 'Virginia Beach'},
        {number: 119, name: 'Reston'},
        {number: 120, name: 'Richmond - Willow Lawn'}
    ],
    'MD': [
        {number: 53, name: 'Hunt Valley'},
        {number: 74, name: 'Owings Mills'},
        {number: 124, name: 'Gambrills'}
    ],
    'NC': [
        {number: 86, name: 'Raleigh'},
        {number: 90, name: 'Cary'},
        {number: 91, name: 'Chapel Hill'},
        {number: 125, name: 'Wake Forest'},
        {number: 126, name: 'Holly Springs'}
    ],
    'MA': [
        {number: 35, name: 'Northborough'},
        {number: 36, name: 'Chestnut Hill'},
        {number: 127, name: 'Medford'},
        {number: 128, name: 'Burlington'},
        {number: 129, name: 'Westwood'},
        {number: 130, name: 'Northborough - 2'}
    ]
};

const STATE_NAMES = {
    'NY': 'New York',
    'PA': 'Pennsylvania',
    'NJ': 'New Jersey',
    'VA': 'Virginia',
    'MD': 'Maryland',
    'NC': 'North Carolina',
    'MA': 'Massachusetts'
};

console.log('🚀 Wegmans Shopping List Builder initialized');
console.log('📝 Console logging enabled for debugging');

// Auto-save configuration
let autoSaveTimer = null;
const AUTO_SAVE_DELAY = 2000; // 2 seconds after last change

function getTodaysListName() {
    return new Date().toLocaleDateString('en-US', {
        weekday: 'long',
        month: 'long',
        day: 'numeric',
        year: 'numeric'
    }); // "Monday, October 28, 2025"
}

async function autoSaveCart() {
    if (cart.length === 0) {
        console.log('📭 Cart empty, skipping auto-save');
        return;
    }

    const listName = getTodaysListName();

    try {
        const response = await auth.fetchWithAuth('/api/lists/auto-save', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ name: listName })
        });

        const data = await response.json();

        if (data.success) {
            const action = data.updated ? 'updated' : 'created';
            console.log(`💾 Auto-saved to "${listName}" (${action})`);

            // Update UI indicator
            updateTodaysListIndicator();
        }
    } catch (error) {
        console.error('Auto-save failed:', error);
    }
}

function scheduleAutoSave() {
    // Debounce: wait 2 seconds after last change before saving
    clearTimeout(autoSaveTimer);
    autoSaveTimer = setTimeout(autoSaveCart, AUTO_SAVE_DELAY);
    console.log('⏰ Auto-save scheduled in 2 seconds...');
}

async function updateTodaysListIndicator() {
    const indicator = document.getElementById('autoSaveIndicator');
    const text = document.getElementById('autoSaveText');

    if (!indicator || !text) return; // Elements not yet loaded

    try {
        const response = await auth.fetchWithAuth('/api/lists/today');
        const data = await response.json();

        if (data.exists) {
            const list = data.list;
            text.textContent = `Saved to: ${list.name} (${list.item_count} items)`;
            indicator.style.display = 'flex';
        } else {
            indicator.style.display = 'none';
        }
    } catch (e) {
        indicator.style.display = 'none';
    }
}

// Load saved cart from API
console.log('💾 Loading saved list...');
async function loadCart() {
    try {
        const response = await auth.fetchWithAuth('/api/cart');
        const data = await response.json();
        if (data.cart && data.cart.length > 0) {
            cart = data.cart;
            console.log('✅ Loaded', data.cart.length, 'items from saved cart');
            renderCart();
        } else {
            console.log('📭 No saved cart found');
        }
    } catch (err) {
        console.log('ℹ️ No previous cart to load (expected on first use)');
    }

    // Update today's list indicator after cart loads
    updateTodaysListIndicator();
}
// IMPORTANT: Wait for auth to initialize before loading cart
// These will be called from auth.js after initialization
// loadCart();
// loadFrequentItems();

// Export for auth.js to call after initialization
window.appReady = async function() {
    console.log('🎬 App ready - Auth initialized, loading list...');

    // Load user's default store from backend
    await loadUserStore();

    // Initialize store selector UI
    initializeStoreSelector();

    loadCart();
    loadFrequentItems();
    loadUserFavorites();
};

async function loadUserStore() {
    try {
        const response = await auth.fetchWithAuth('/api/store');
        const data = await response.json();

        selectedStore = data.store_number.toString();
        localStorage.setItem('selectedStore', selectedStore);

        console.log(`🏪 User default store: ${selectedStore}`);
    } catch (error) {
        console.error('Failed to load user store:', error);
        selectedStore = '86'; // Fallback to Raleigh
    }
}

// ====== Store Selection Functions ======

function initializeStoreSelector() {
    // Find which state the current store is in
    let foundState = null;
    for (const [state, stores] of Object.entries(WEGMANS_STORES)) {
        if (stores.some(s => s.number.toString() === selectedStore)) {
            foundState = state;
            break;
        }
    }

    if (foundState) {
        // Set state selector
        const stateSelector = document.getElementById('stateSelector');
        stateSelector.value = foundState;

        // Populate store options for this state
        updateStoreOptions();

        // Set store selector
        const storeSelector = document.getElementById('storeSelector');
        storeSelector.value = selectedStore;

        const storeName = storeSelector.options[storeSelector.selectedIndex]?.text || 'Unknown';
        console.log(`🏪 Store initialized: ${storeName} (${selectedStore})`);
    } else {
        console.warn(`⚠️ Store ${selectedStore} not found in store list, defaulting to Raleigh`);
        selectedStore = '86';
        initializeStoreSelector(); // Retry with default
    }
}

function updateStoreOptions() {
    const stateSelector = document.getElementById('stateSelector');
    const storeSelector = document.getElementById('storeSelector');
    const state = stateSelector.value;

    if (!state) {
        storeSelector.disabled = true;
        storeSelector.innerHTML = '<option value="">Select Store</option>';
        return;
    }

    // Populate stores for selected state
    const stores = WEGMANS_STORES[state] || [];
    storeSelector.innerHTML = '<option value="">Select Store</option>';

    stores.forEach(store => {
        const option = document.createElement('option');
        option.value = store.number;
        option.textContent = store.name;
        storeSelector.appendChild(option);
    });

    storeSelector.disabled = false;
    console.log(`📍 Loaded ${stores.length} stores for ${STATE_NAMES[state]}`);
}

// Store for pending store change
let pendingStoreChange = null;

function changeStore() {
    const storeSelector = document.getElementById('storeSelector');
    const newStore = storeSelector.value;

    if (!newStore || newStore === selectedStore) {
        return; // No change
    }

    // Check if user has data in current cart/favorites
    const hasData = cart.length > 0 || userFavorites.size > 0;

    if (hasData) {
        // Show warning modal
        pendingStoreChange = newStore;
        const storeName = storeSelector.options[storeSelector.selectedIndex].text;
        const stateSelector = document.getElementById('stateSelector');
        const stateName = STATE_NAMES[stateSelector.value] || 'different';

        document.getElementById('switchStoreMessage').innerHTML = `
            <p style="font-size: var(--font-size-base); margin-bottom: var(--space-3);">
                You're about to switch to <strong>${storeName}</strong> in ${stateName}.
            </p>
            <p style="font-size: var(--font-size-sm); margin-bottom: var(--space-3);">
                You currently have <strong>${cart.length} item(s)</strong> in your list
                ${userFavorites.size > 0 ? `and <strong>${userFavorites.size} favorite(s)</strong>` : ''}.
            </p>
            <p style="font-size: var(--font-size-sm); color: var(--warning-orange); font-weight: var(--font-weight-semibold);">
                Your data will remain at your current store. Switching will show ${storeName}'s data instead.
            </p>
        `;
        openModal('switchStoreModal');
    } else {
        // No data, switch immediately
        performStoreSwitch(newStore);
    }
}

async function confirmStoreSwitch() {
    closeModal('switchStoreModal');
    await performStoreSwitch(pendingStoreChange);
    pendingStoreChange = null;
}

function cancelStoreSwitch() {
    closeModal('switchStoreModal');

    // Revert dropdowns to current store
    initializeStoreSelector();
    pendingStoreChange = null;
}

async function performStoreSwitch(newStore) {
    try {
        const storeSelector = document.getElementById('storeSelector');

        // Re-populate options if needed to get the store name
        const stateSelector = document.getElementById('stateSelector');
        if (!storeSelector.options.length || storeSelector.options.length === 1) {
            updateStoreOptions();
            storeSelector.value = newStore;
        }

        const storeName = storeSelector.options[storeSelector.selectedIndex]?.text || `Store ${newStore}`;

        // Update backend
        const response = await auth.fetchWithAuth('/api/store', {
            method: 'PUT',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ store_number: parseInt(newStore) })
        });

        if (!response.ok) {
            throw new Error('Failed to update store');
        }

        // Update local state
        selectedStore = newStore;
        localStorage.setItem('selectedStore', selectedStore);

        showToast(`Switched to ${storeName}`);
        console.log(`🏪 Store switched to: ${storeName} (${newStore})`);

        // Clear UI (data is store-specific now)
        cart = [];
        userFavorites.clear();
        renderCart();

        // Clear search results
        document.getElementById('resultsGrid').innerHTML = '';
        document.getElementById('resultsSection').style.display = 'none';
        document.getElementById('emptyResults').style.display = 'block';
        currentSearchTerm = '';
        currentSearchResults = [];

        // Reload store-specific data
        await loadCart();
        await loadFrequentItems();
        await loadUserFavorites();

    } catch (error) {
        console.error('Failed to switch store:', error);
        showToast('Failed to switch stores - please try again', true);

        // Revert dropdowns
        initializeStoreSelector();
    }
}

// ====== Favorites Functions ======

async function loadUserFavorites() {
    try {
        const response = await auth.fetchWithAuth('/api/favorites');
        const data = await response.json();

        userFavorites = new Set(data.favorites.map(item => item.product_name));
        console.log(`⭐ Loaded ${userFavorites.size} favorites`);
    } catch (error) {
        console.error('Failed to load favorites:', error);
        userFavorites = new Set();
    }
}

function isFavorited(productName) {
    return userFavorites.has(productName);
}

async function toggleFavorite(product, event) {
    // Prevent card click from firing
    event.stopPropagation();

    const productName = product.name;
    const wasFavorited = userFavorites.has(productName);

    // Store button reference BEFORE async calls (event.currentTarget becomes null)
    const starBtn = event.currentTarget;
    const starIcon = starBtn ? starBtn.querySelector('.star-icon') : null;

    try {
        if (wasFavorited) {
            // Show confirmation modal for unfavoriting
            window.productToUnfavorite = { product, starBtn, starIcon };
            document.getElementById('removeFavoriteMessage').textContent =
                `Remove "${product.name}" from your favorites?`;
            openModal('removeFavoriteModal');
        } else {
            // Add to favorites
            const response = await auth.fetchWithAuth('/api/favorites/add', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    product_name: product.name,
                    price: product.price,
                    aisle: product.aisle,
                    image_url: product.image || '',
                    is_sold_by_weight: product.is_sold_by_weight || false
                })
            });

            if (response.ok) {
                userFavorites.add(productName);
                showToast('⭐ Added to favorites');

                // Update UI (safe because we stored reference)
                if (starBtn) {
                    starBtn.classList.add('favorited');
                    if (starIcon) starIcon.classList.add('filled');
                }

                // Reload frequent items to update display
                await loadFrequentItems();
            }
        }
    } catch (error) {
        console.error('Failed to toggle favorite:', error);
        showToast('Failed to update favorites', true);
    }
}

// Load both favorites and frequent items
async function loadFrequentItems() {
    console.log('⭐ Loading favorites and frequent items from database...');

    try {
        // Load both in parallel
        const [favoritesResponse, frequentResponse] = await Promise.all([
            auth.fetchWithAuth('/api/favorites'),
            auth.fetchWithAuth('/api/frequent')
        ]);

        const favoritesData = await favoritesResponse.json();
        const frequentData = await frequentResponse.json();

        const favorites = favoritesData.favorites || [];
        const frequent = frequentData.items || [];

        // ALWAYS render favorites section (even if empty)
        const favoritesSection = document.getElementById('favoritesSection');
        const favoritesContainer = document.getElementById('favoriteItems');

        if (favorites.length > 0) {
            const favoriteItems = favorites.slice(0, 8).map(item => ({
                product: {
                    name: item.product_name,
                    price: typeof item.price === 'number' ? `$${item.price.toFixed(2)}` : item.price,
                    aisle: item.aisle,
                    image: item.image_url,
                    is_sold_by_weight: item.is_sold_by_weight || false
                },
                count: item.purchase_count
            }));

            console.log(`✅ Found ${favoriteItems.length} favorites`);
            renderFavorites(favoriteItems);
            fetchMissingImagesForItems(favoriteItems, true);
        } else {
            // No favorites - hide section
            console.log('📭 No favorites at this store');
            favoritesContainer.innerHTML = '';
            favoritesSection.style.display = 'none';
        }

        // ALWAYS render frequent items section (even if empty)
        const frequentSection = document.getElementById('frequentSection');
        const frequentContainer = document.getElementById('frequentItems');

        if (frequent.length > 0) {
            const frequentItems = frequent.slice(0, 8).map(item => ({
                product: {
                    name: item.product_name,
                    price: typeof item.price === 'number' ? `$${item.price.toFixed(2)}` : item.price,
                    aisle: item.aisle,
                    image: item.image_url,
                    is_sold_by_weight: item.is_sold_by_weight || false
                },
                count: item.purchase_count
            }));

            console.log(`✅ Found ${frequentItems.length} frequently bought items`);
            renderFrequentItems(frequentItems);
            fetchMissingImagesForItems(frequentItems, false);
        } else {
            // No frequent items - hide section
            console.log('📭 No frequently bought items at this store');
            frequentContainer.innerHTML = '';
            frequentSection.style.display = 'none';
        }

    } catch (error) {
        console.log('  No favorites or frequent items yet (expected on first use)');
        // On error, hide both sections
        const favoritesSection = document.getElementById('favoritesSection');
        const frequentSection = document.getElementById('frequentSection');
        if (favoritesSection) favoritesSection.style.display = 'none';
        if (frequentSection) frequentSection.style.display = 'none';
    }
}

async function fetchMissingImagesForItems(items, isFavorites) {
    // Find items without images
    const itemsNeedingImages = items.filter(item => !item.product.image);

    if (itemsNeedingImages.length === 0) {
        return;
    }

    const sectionName = isFavorites ? 'favorites' : 'frequent items';
    console.log(`🖼️  Fetching images for ${itemsNeedingImages.length} ${sectionName} (parallel batch)...`);

    try {
        // Batch API call - fetch all images in one request
        const productNames = itemsNeedingImages.map(item => item.product.name);

        const response = await auth.fetchWithAuth('/api/images/fetch', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ product_names: productNames })
        });

        const data = await response.json();

        // Update images in memory
        let updatedCount = 0;
        data.results.forEach(result => {
            if (result.success && result.image_url) {
                const item = itemsNeedingImages.find(i => i.product.name === result.product_name);
                if (item) {
                    item.product.image = result.image_url;
                    updatedCount++;
                }
            }
        });

        if (updatedCount > 0) {
            // Re-render once with all updated images
            if (isFavorites) {
                renderFavorites(items);
            } else {
                renderFrequentItems(items);
            }
            console.log(`✅ Updated ${updatedCount} images (${data.success_count}/${data.total_count} found)`);
        } else {
            console.log('ℹ️  No new images found');
        }

    } catch (error) {
        console.error('❌ Failed to fetch images:', error);
    }
}

function renderFavorites(favoriteItems) {
    const section = document.getElementById('favoritesSection');
    const container = document.getElementById('favoriteItems');

    container.innerHTML = ''; // Clear existing

    favoriteItems.forEach(item => {
        const product = item.product;

        // Create card
        const card = document.createElement('div');
        card.className = 'frequent-item favorite-item-card';
        card.onclick = () => showQuantityModal(product);

        // Add star button (always favorited in this section)
        const starBtn = document.createElement('button');
        starBtn.className = 'btn-favorite favorited btn-favorite-small';
        starBtn.title = 'Remove from favorites';
        starBtn.onclick = (e) => toggleFavorite(product, e);
        starBtn.innerHTML = `
            <svg class="star-icon filled"
                 width="18" height="18" viewBox="0 0 24 24"
                 fill="currentColor"
                 stroke="currentColor" stroke-width="2">
                <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon>
            </svg>
        `;
        card.appendChild(starBtn);

        // Add image or placeholder
        if (product.image) {
            const img = document.createElement('img');
            img.src = product.image;
            img.className = 'frequent-item-image';
            img.alt = product.name;
            img.onerror = function() {
                this.style.display = 'none';
                this.nextElementSibling.style.display = 'flex';
            };
            card.appendChild(img);

            const placeholder = document.createElement('div');
            placeholder.className = 'frequent-item-image-placeholder';
            placeholder.style.display = 'none';
            placeholder.innerHTML = `
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="40" height="40">
                    <circle cx="9" cy="21" r="1"></circle>
                    <circle cx="20" cy="21" r="1"></circle>
                    <path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"></path>
                </svg>
            `;
            card.appendChild(placeholder);
        } else {
            const placeholder = document.createElement('div');
            placeholder.className = 'frequent-item-image-placeholder';
            placeholder.innerHTML = `
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="40" height="40">
                    <circle cx="9" cy="21" r="1"></circle>
                    <circle cx="20" cy="21" r="1"></circle>
                    <path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"></path>
                </svg>
            `;
            card.appendChild(placeholder);
        }

        // Add product name
        const name = document.createElement('div');
        name.className = 'frequent-item-name';
        name.textContent = product.name;
        card.appendChild(name);

        // Add footer with price and badge
        const footer = document.createElement('div');
        footer.className = 'frequent-item-footer';
        footer.innerHTML = `
            <span class="frequent-item-price">${escapeHtml(product.price)}</span>
            <span class="favorite-badge" title="You starred this item">⭐ Favorite</span>
        `;
        card.appendChild(footer);

        container.appendChild(card);
    });

    section.style.display = 'block';
}

function renderFrequentItems(frequentItems) {
    const section = document.getElementById('frequentSection');
    const container = document.getElementById('frequentItems');

    let html = '';
    frequentItems.forEach(item => {
        const product = item.product;

        // Add weight badge for frequent items
        const weightBadge = product.is_sold_by_weight
            ? `<div class="weight-badge-mini">⚖️ ${product.sell_by_unit || 'lb'}</div>`
            : '';

        const imageHtml = product.image
            ? `<div class="frequent-item-image-container">
                   <img src="${escapeHtml(product.image)}" class="frequent-item-image" alt="${escapeHtml(product.name)}" onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';">
                   <div class="frequent-item-image-placeholder" style="display: none;">
                       <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="40" height="40">
                           <circle cx="9" cy="21" r="1"></circle>
                           <circle cx="20" cy="21" r="1"></circle>
                           <path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"></path>
                       </svg>
                   </div>
                   ${weightBadge}
               </div>`
            : `<div class="frequent-item-image-container">
                   <div class="frequent-item-image-placeholder">
                       <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="40" height="40">
                           <circle cx="9" cy="21" r="1"></circle>
                           <circle cx="20" cy="21" r="1"></circle>
                           <path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"></path>
                       </svg>
                   </div>
                   ${weightBadge}
               </div>`;

        // Format price with unit price for weight items
        let priceDisplay = escapeHtml(product.price);
        if (product.is_sold_by_weight && product.unit_price) {
            priceDisplay += ` <span class="unit-price-mini">${escapeHtml(product.unit_price)}</span>`;
        }

        html += `
            <div class="frequent-item" onclick='showQuantityModal(${JSON.stringify(product)})'>
                ${imageHtml}
                <div class="frequent-item-name">${escapeHtml(product.name)}</div>
                <div class="frequent-item-footer">
                    <span class="frequent-item-price">${priceDisplay}</span>
                    <span class="frequent-item-badge" title="Appears in ${item.count} past lists">In ${item.count} lists</span>
                </div>
            </div>
        `;
    });

    container.innerHTML = html;
    section.style.display = 'block';
}

// Quantity modal state
let currentProductForQuantity = null;

function showQuantityModal(product) {
    console.log('📊 Opening quantity modal for:', product.name);
    currentProductForQuantity = product;

    // Set product info
    document.getElementById('qtyProductName').textContent = product.name;
    document.getElementById('qtyProductPrice').textContent = product.price;

    // Configure for weight items vs count items
    const weightHint = document.getElementById('weightItemHint');
    const slider = document.getElementById('quantitySlider');
    const customInput = document.getElementById('customQuantityInput');
    const quantityLabel = document.getElementById('quantitySelectorLabel');

    if (product.is_sold_by_weight) {
        // Weight item - show hint and allow decimals
        const unit = product.sell_by_unit || 'lb';
        const unitPlural = getPluralUnit(unit);

        // Show weight hint
        weightHint.style.display = 'flex';
        document.getElementById('weightUnitName').textContent = unit;
        document.getElementById('weightExample').textContent = '1.5';

        // Update label
        quantityLabel.textContent = `Select ${capitalizeFirst(unitPlural)} (0.1-10)`;

        // Configure slider for decimals (use 0.5 increments displayed as decimals)
        slider.min = '1';
        slider.max = '20';
        slider.value = '2';
        slider.step = '1';

        // Configure custom input for decimals
        customInput.min = '0.1';
        customInput.max = '99.9';
        customInput.step = '0.1';
        customInput.placeholder = `e.g., 1.5 ${unitPlural}`;

        // Reset form to 1.0
        document.getElementById('quantityDisplay').textContent = '1';
        customInput.value = '';

    } else {
        // Count item - hide hint, use integers
        weightHint.style.display = 'none';
        quantityLabel.textContent = 'Select Quantity (1-10)';

        // Configure for integers
        slider.min = '1';
        slider.max = '10';
        slider.value = '1';
        slider.step = '1';

        customInput.min = '1';
        customInput.max = '999';
        customInput.step = '1';
        customInput.placeholder = 'e.g., 20';

        // Reset form
        document.getElementById('quantityDisplay').textContent = '1';
        customInput.value = '';
    }

    // Show modal
    const modal = document.getElementById('quantityModal');
    modal.classList.add('show');

    // Setup slider listener
    slider.oninput = function() {
        // For weight items, slider shows 1-20 which maps to 0.5-10.0 in 0.5 increments
        if (product.is_sold_by_weight) {
            const value = parseFloat(this.value) / 2.0;
            document.getElementById('quantityDisplay').textContent = value.toFixed(1);
        } else {
            document.getElementById('quantityDisplay').textContent = this.value;
        }
        customInput.value = ''; // Clear custom input
    };

    // Setup custom input listener
    customInput.oninput = function() {
        if (this.value) {
            document.getElementById('quantityDisplay').textContent = this.value;
        }
    };

    // ESC and backdrop close
    openModal('quantityModal');
}

// Helper function to get plural unit names
function getPluralUnit(unit) {
    const plurals = {
        'lb': 'lbs',
        'oz': 'oz',
        'kg': 'kg',
        'g': 'g',
        'pkg': 'packages',
        'Each': 'items'
    };
    return plurals[unit] || unit + 's';
}

// Helper function to capitalize first letter
function capitalizeFirst(str) {
    return str.charAt(0).toUpperCase() + str.slice(1);
}

function closeQuantityModal() {
    closeModal('quantityModal');
    currentProductForQuantity = null;
}

async function confirmAddQuantity() {
    if (!currentProductForQuantity) return;

    // Get quantity from custom input or from the display (which shows the correct value)
    const customQty = parseFloat(document.getElementById('customQuantityInput').value);
    const displayQty = parseFloat(document.getElementById('quantityDisplay').textContent);
    const quantity = customQty || displayQty;

    console.log('⚡ Adding to list with quantity:', quantity, '-', currentProductForQuantity.name);

    // INSTANT: Close modal immediately (optimistic UI)
    closeModal('quantityModal');
    showToast(`✓ Adding ${quantity} to cart...`);

    // Call API to add to cart (in background)
    try {
        const response = await auth.fetchWithAuth('/api/cart/add', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                name: currentProductForQuantity.name,
                price: currentProductForQuantity.price,
                quantity: quantity,
                aisle: currentProductForQuantity.aisle,
                image: currentProductForQuantity.image,
                search_term: currentProductForQuantity.search_term || 'frequent',
                is_sold_by_weight: currentProductForQuantity.is_sold_by_weight || false,
                unit_price: currentProductForQuantity.unit_price || null,
                sell_by_unit: currentProductForQuantity.sell_by_unit || 'Each'
            })
        });

        if (!response.ok) {
            let errorText = await response.text();
            try {
                const errorJson = JSON.parse(errorText);
                errorText = errorJson.detail || errorText;
            } catch (e) {
                // Not JSON, use as is
            }
            throw new Error(`Server error ${response.status}: ${errorText.substring(0, 200)}`);
        }

        const data = await response.json();

        // Update cart from server response
        cart = data.cart;
        renderCart();

        // AUTO-SAVE after cart change
        scheduleAutoSave();

        // Update toast to show success
        showToast(`✓ Added ${quantity} to cart`);

        // Bounce animation
        const cartCount = document.getElementById('cartCount');
        cartCount.classList.remove('bounce');
        void cartCount.offsetWidth;
        cartCount.classList.add('bounce');
        setTimeout(() => cartCount.classList.remove('bounce'), 300);

    } catch (error) {
        showToast('Failed to add to cart', true);
        console.error('Add to cart error:', error);

        // Show detailed error on mobile for debugging
        if (window.innerWidth <= 767) {
            const errorDiv = document.createElement('div');
            errorDiv.style.cssText = 'position:fixed;top:50%;left:10px;right:10px;background:red;color:white;padding:20px;z-index:9999;font-size:12px;border-radius:8px;';
            errorDiv.innerHTML = `<strong>Error:</strong><br>${error.message}<br><br>Check response status`;
            document.body.appendChild(errorDiv);
            setTimeout(() => errorDiv.remove(), 5000);
        }
    }

    // Close modal
    closeQuantityModal();
}

function quickAddToCart(product) {
    // This is still used by individual item add in saved lists
    // For now, just add 1 directly (could also open modal if desired)
    console.log('⚡ Quick-adding to cart:', product.name);

    const existing = cart.find(item => item.name === product.name);
    if (existing) {
        existing.quantity += 1;
        showToast('✓ Increased quantity');
    } else {
        cart.push({
            ...product,
            quantity: 1,
            search_term: product.search_term || 'frequent'
        });
        showToast('✓ Added to list');
    }

    saveCart();
    renderCart();

    // Bounce animation
    const cartCount = document.getElementById('cartCount');
    cartCount.classList.remove('bounce');
    void cartCount.offsetWidth;
    cartCount.classList.add('bounce');
    setTimeout(() => cartCount.classList.remove('bounce'), 300);
}

// Helper functions
function showLoading(message = 'Searching Wegmans...') {
    document.getElementById('loadingText').textContent = message;
    document.getElementById('loadingOverlay').classList.add('show');
}

function hideLoading() {
    document.getElementById('loadingOverlay').classList.remove('show');
}

function showToast(message, isError = false) {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.className = 'toast show';
    if (isError) toast.classList.add('error');
    setTimeout(() => toast.classList.remove('show'), 3000);
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Generic modal functions
function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (!modal) return;

    modal.classList.add('show');
    console.log('📂 Modal opened:', modalId);

    // Close on ESC key
    const handleEscape = (e) => {
        if (e.key === 'Escape') {
            closeModal(modalId);
        }
    };

    // Close on backdrop click (clicking outside modal content)
    const handleBackdropClick = (e) => {
        if (e.target === modal) {
            closeModal(modalId);
        }
    };

    // Add event listeners
    document.addEventListener('keydown', handleEscape);
    modal.addEventListener('click', handleBackdropClick);

    // Store handlers so we can remove them later
    modal._escapeHandler = handleEscape;
    modal._backdropHandler = handleBackdropClick;
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (!modal) return;

    modal.classList.remove('show');
    console.log('📂 Modal closed:', modalId);

    // Remove event listeners
    if (modal._escapeHandler) {
        document.removeEventListener('keydown', modal._escapeHandler);
        modal.removeEventListener('click', modal._backdropHandler);
        modal._escapeHandler = null;
        modal._backdropHandler = null;
    }
}

// Search functionality
async function searchProducts() {
    const searchTerm = document.getElementById('searchInput').value.trim();
    console.log('🔍 Search initiated for:', searchTerm);

    if (!searchTerm) {
        console.warn('⚠️ No search term provided');
        showToast('Please enter a search term', true);
        return;
    }

    // Reset pagination state for new search
    currentSearchTerm = searchTerm;
    currentSearchResults = [];

    showLoading(`Searching for "${searchTerm}"...`);
    document.getElementById('searchBtn').disabled = true;

    try {
        console.log('📡 Sending search request...');
        const response = await auth.fetchWithAuth('/api/search', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                search_term: searchTerm,
                max_results: RESULTS_PER_PAGE,
                offset: 0,
                store_number: parseInt(selectedStore)
            })
        });

        console.log('📥 Response status:', response.status);

        if (!response.ok) {
            throw new Error(`Search failed with status ${response.status}`);
        }

        const data = await response.json();
        console.log('📦 Response data:', data);

        // Extract products array from response
        const products = data.products || data;
        const fromCache = data.from_cache;
        console.log('✅ Products array:', products, '(length:', products.length, ')');
        if (fromCache) {
            console.log('💾 Loaded from cache');
        }

        hideLoading();

        if (products.length === 0) {
            console.log('❌ No products found');
            showToast('No products found', true);
            document.getElementById('emptyResults').innerHTML =
                '<p class="text-lg">No results found</p><p class="mt-3">Try a different search term</p>';
            document.getElementById('resultsSection').style.display = 'none';
            document.getElementById('emptyResults').style.display = 'block';

            // Show frequently bought again when no results
            const frequentSection = document.getElementById('frequentSection');
            if (frequentSection && frequentSection.children.length > 0) {
                frequentSection.style.display = 'block';
            }

            // Hide load more button
            document.getElementById('loadMoreBtn').style.display = 'none';
        } else {
            console.log('🎉 Displaying', products.length, 'products');
            currentSearchResults = products;
            displayResults(products, searchTerm);

            // Show/hide "Load More" button
            if (products.length >= RESULTS_PER_PAGE) {
                document.getElementById('loadMoreBtn').style.display = 'block';
            } else {
                document.getElementById('loadMoreBtn').style.display = 'none';
            }
        }

    } catch (error) {
        console.error('❌ Search error:', error);
        hideLoading();
        showToast('Search failed: ' + error.message, true);
    } finally {
        document.getElementById('searchBtn').disabled = false;
    }
}

// Enter key to search
document.getElementById('searchInput').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') searchProducts();
});

// Load more results (pagination)
async function loadMoreResults() {
    if (!currentSearchTerm) {
        console.warn('⚠️ No active search to load more from');
        return;
    }

    const currentOffset = currentSearchResults.length;
    console.log(`📄 Loading more results for "${currentSearchTerm}" (offset: ${currentOffset})...`);

    const loadMoreBtn = document.getElementById('loadMoreBtn');
    loadMoreBtn.disabled = true;
    loadMoreBtn.textContent = 'Loading...';

    try {
        const response = await auth.fetchWithAuth('/api/search', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                search_term: currentSearchTerm,
                max_results: RESULTS_PER_PAGE,
                offset: currentOffset,
                store_number: parseInt(selectedStore)
            })
        });

        if (!response.ok) {
            throw new Error(`Load more failed with status ${response.status}`);
        }

        const data = await response.json();
        const products = data.products || data;

        console.log(`✅ Loaded ${products.length} more products`);

        if (products.length === 0) {
            showToast('No more results');
            loadMoreBtn.style.display = 'none';
            return;
        }

        // Append new products to current results
        currentSearchResults = currentSearchResults.concat(products);

        // Append to display
        appendResults(products);

        // Show/hide button based on if we got a full page
        if (products.length < RESULTS_PER_PAGE) {
            loadMoreBtn.style.display = 'none';
            showToast(`Showing all ${currentSearchResults.length} results`);
        } else {
            loadMoreBtn.style.display = 'block';
            loadMoreBtn.textContent = 'Load More Results';
        }

    } catch (error) {
        console.error('❌ Load more error:', error);
        showToast('Failed to load more results', true);
        loadMoreBtn.textContent = 'Load More Results';
    } finally {
        loadMoreBtn.disabled = false;
    }
}

function appendResults(products) {
    console.log('📎 Appending', products.length, 'more products to results...');

    const grid = document.getElementById('resultsGrid');

    products.forEach((product, index) => {
        const card = document.createElement('div');
        card.className = 'product-card';
        card.onclick = () => showQuantityModal(product);

        // Add star button
        const favorited = isFavorited(product.name);
        const starBtn = document.createElement('button');
        starBtn.className = `btn-favorite ${favorited ? 'favorited' : ''}`;
        starBtn.title = favorited ? 'Remove from favorites' : 'Add to favorites';
        starBtn.onclick = (e) => toggleFavorite(product, e);
        starBtn.innerHTML = `
            <svg class="star-icon ${favorited ? 'filled' : ''}"
                 width="20" height="20" viewBox="0 0 24 24"
                 fill="${favorited ? 'currentColor' : 'none'}"
                 stroke="currentColor" stroke-width="2">
                <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon>
            </svg>
        `;
        card.appendChild(starBtn);

        // Add image or placeholder using DOM (not innerHTML)
        if (product.image) {
            const img = document.createElement('img');
            img.src = product.image;
            img.className = 'product-image';
            img.alt = product.name;
            img.onerror = function() {
                this.src = 'data:image/svg+xml,%3Csvg xmlns=%27http://www.w3.org/2000/svg%27 viewBox=%270 0 24 24%27 fill=%27none%27 stroke=%27%23999%27 stroke-width=%271.5%27%3E%3Ccircle cx=%279%27 cy=%2721%27 r=%271%27/%3E%3Ccircle cx=%2720%27 cy=%2721%27 r=%271%27/%3E%3Cpath d=%27M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6%27/%3E%3C/svg%3E';
            };
            card.appendChild(img);
        } else {
            const placeholder = document.createElement('div');
            placeholder.className = 'product-image';
            placeholder.style.cssText = 'display: flex; align-items: center; justify-content: center; background: var(--gray-100);';
            placeholder.innerHTML = `
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="60" height="60">
                    <circle cx="9" cy="21" r="1"></circle>
                    <circle cx="20" cy="21" r="1"></circle>
                    <path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"></path>
                </svg>
            `;
            card.appendChild(placeholder);
        }

        // Add product name
        const nameDiv = document.createElement('div');
        nameDiv.className = 'product-name';
        nameDiv.textContent = product.name;
        card.appendChild(nameDiv);

        // Add product info
        const infoDiv = document.createElement('div');
        infoDiv.className = 'product-info';
        infoDiv.innerHTML = `
            <span class="product-price">${escapeHtml(product.price)}</span>
            <span class="product-aisle">${escapeHtml(product.aisle)}</span>
        `;
        card.appendChild(infoDiv);

        grid.appendChild(card);
    });

    console.log('✅ Appended successfully');
}

function displayResults(products, searchTerm) {
    console.log('🎨 Displaying results for:', searchTerm, '- Products:', products.length);

    document.getElementById('emptyResults').style.display = 'none';
    document.getElementById('resultsSection').style.display = 'block';

    // Hide frequently bought when showing search results
    const frequentSection = document.getElementById('frequentSection');
    if (frequentSection) {
        frequentSection.style.display = 'none';
    }

    const grid = document.getElementById('resultsGrid');
    grid.innerHTML = '';

    products.forEach((product, index) => {
        console.log(`  📦 Product ${index + 1}:`, product.name, '-', product.price);

        const card = document.createElement('div');
        card.className = 'product-card';
        card.onclick = () => showQuantityModal(product);

        // Add star button
        const favorited = isFavorited(product.name);
        const starBtn = document.createElement('button');
        starBtn.className = `btn-favorite ${favorited ? 'favorited' : ''}`;
        starBtn.title = favorited ? 'Remove from favorites' : 'Add to favorites';
        starBtn.onclick = (e) => toggleFavorite(product, e);
        starBtn.innerHTML = `
            <svg class="star-icon ${favorited ? 'filled' : ''}"
                 width="20" height="20" viewBox="0 0 24 24"
                 fill="${favorited ? 'currentColor' : 'none'}"
                 stroke="currentColor" stroke-width="2">
                <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon>
            </svg>
        `;
        card.appendChild(starBtn);

        // Add image or placeholder using DOM (not innerHTML)
        const imageContainer = document.createElement('div');
        imageContainer.className = 'product-image-container';

        if (product.image) {
            const img = document.createElement('img');
            img.src = product.image;
            img.className = 'product-image';
            img.alt = product.name;
            img.onerror = function() {
                this.src = 'data:image/svg+xml,%3Csvg xmlns=%27http://www.w3.org/2000/svg%27 viewBox=%270 0 24 24%27 fill=%27none%27 stroke=%27%23999%27 stroke-width=%271.5%27%3E%3Ccircle cx=%279%27 cy=%2721%27 r=%271%27/%3E%3Ccircle cx=%2720%27 cy=%2721%27 r=%271%27/%3E%3Cpath d=%27M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6%27/%3E%3C/svg%3E';
            };
            imageContainer.appendChild(img);
        } else {
            const placeholder = document.createElement('div');
            placeholder.className = 'product-image';
            placeholder.style.cssText = 'display: flex; align-items: center; justify-content: center; background: var(--gray-100);';
            placeholder.innerHTML = `
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="60" height="60">
                    <circle cx="9" cy="21" r="1"></circle>
                    <circle cx="20" cy="21" r="1"></circle>
                    <path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"></path>
                </svg>
            `;
            imageContainer.appendChild(placeholder);
        }

        // Add weight badge if sold by weight
        if (product.is_sold_by_weight) {
            const weightBadge = document.createElement('div');
            weightBadge.className = 'weight-badge';
            const unit = product.sell_by_unit || 'lb';
            weightBadge.textContent = `sold by ${unit}`;
            imageContainer.appendChild(weightBadge);
        }

        card.appendChild(imageContainer);

        // Add product name
        const nameDiv = document.createElement('div');
        nameDiv.className = 'product-name';
        nameDiv.textContent = product.name;
        card.appendChild(nameDiv);

        // Add product info with unit price for weight items
        const infoDiv = document.createElement('div');
        infoDiv.className = 'product-info';

        let infoHTML = `<span class="product-price">${escapeHtml(product.price)}</span>`;

        // Add unit price if weight item
        if (product.is_sold_by_weight && product.unit_price) {
            infoHTML += `<span class="unit-price">${escapeHtml(product.unit_price)}</span>`;
        }

        infoHTML += `<span class="product-aisle">${escapeHtml(product.aisle)}</span>`;

        infoDiv.innerHTML = infoHTML;
        card.appendChild(infoDiv);

        grid.appendChild(card);
    });

    console.log('✅ Results displayed successfully');
}

function addToCart(product, searchTerm) {
    console.log('🛒 Adding to list:', product.name);

    // Check if item already in cart
    const existing = cart.find(item => item.name === product.name);
    if (existing) {
        existing.quantity += 1;
        console.log('  ⬆️ Increased quantity to:', existing.quantity);
        showToast('✓ Increased quantity');
    } else {
        cart.push({
            ...product,
            quantity: 1,
            search_term: searchTerm
        });
        console.log('  ➕ Added new item to cart');
        showToast('✓ Added to list');
    }

    console.log('🛒 Cart now has', cart.length, 'unique items');
    saveCart();
    renderCart();

    // Bounce animation on cart count badge
    const cartCount = document.getElementById('cartCount');
    cartCount.classList.remove('bounce');
    // Force reflow to restart animation
    void cartCount.offsetWidth;
    cartCount.classList.add('bounce');
    setTimeout(() => cartCount.classList.remove('bounce'), 300);

    // Clear search and show frequently bought again
    document.getElementById('searchInput').value = '';
    document.getElementById('resultsSection').style.display = 'none';
    document.getElementById('emptyResults').style.display = 'block';
    document.getElementById('emptyResults').innerHTML =
        '<p class="text-lg">👆 Search for another product</p>';

    // Show frequently bought section again
    const frequentSection = document.getElementById('frequentSection');
    if (frequentSection && frequentSection.children.length > 0) {
        frequentSection.style.display = 'block';
    }
}

function renderCart() {
    console.log('🎨 Rendering cart with', cart.length, 'items');

    const cartItems = document.getElementById('cartItems');
    const cartCount = document.getElementById('cartCount');
    const viewListBtn = document.getElementById('viewListBtn');

    if (cart.length === 0) {
        console.log('  📭 Cart is empty');
        cartItems.innerHTML = '<div class="empty-cart"><div class="emoji"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="48" height="48"><circle cx="9" cy="21" r="1"></circle><circle cx="20" cy="21" r="1"></circle><path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"></path></svg></div><p style="font-weight: 600; color: var(--text-primary); margin-bottom: var(--space-2);">Your list is empty</p><p class="text-xs">Start searching to add items!</p></div>';
        cartCount.textContent = '0';
        document.getElementById('cartTotals').style.display = 'none';
        document.getElementById('exportBtn').style.display = 'none';
        document.getElementById('printListBtn').style.display = 'none';
        document.getElementById('saveCustomBtn').style.display = 'none';
        return;
    }

    let html = '';
    let subtotal = 0;
    let totalItems = 0;

    cart.forEach((item, index) => {
        const qty = item.quantity;

        // Handle both string ("$2.49") and number (2.49) from database
        const price = typeof item.price === 'string'
            ? parseFloat(item.price.replace('$', ''))
            : parseFloat(item.price);
        const itemTotal = price * qty;
        subtotal += itemTotal;
        totalItems += qty;

        // Handle field name differences (database vs local)
        const displayName = item.product_name || item.name;
        const displayPrice = typeof item.price === 'number' ? `$${item.price.toFixed(2)}` : item.price;
        const displayAisle = item.aisle || 'Unknown';

        // Format quantity with units for weight items
        let qtyDisplay = qty;
        let qtyInputStep = '1';
        let qtyInputMin = '1';
        if (item.is_sold_by_weight) {
            const unit = item.sell_by_unit || 'lb';
            const unitPlural = getPluralUnit(unit);
            qtyDisplay = `${qty} ${unitPlural}`;
            qtyInputStep = '0.1';
            qtyInputMin = '0.1';
        }

        // Add weight badge for cart items
        const weightBadge = item.is_sold_by_weight
            ? '<span class="cart-weight-badge">⚖️</span>'
            : '';

        html += `
            <div class="cart-item">
                <div class="cart-item-qty-container">
                    <input type="number" class="cart-item-qty" value="${qty}" min="${qtyInputMin}" step="${qtyInputStep}"
                        onchange="updateQuantity(${index}, this.value)">
                    ${item.is_sold_by_weight ? `<span class="cart-qty-unit">${getPluralUnit(item.sell_by_unit || 'lb')}</span>` : ''}
                </div>
                <div class="cart-item-details">
                    <div class="cart-item-name">
                        ${weightBadge}
                        ${escapeHtml(displayName)}
                    </div>
                    <div class="cart-item-meta">
                        ${escapeHtml(displayPrice)}${item.is_sold_by_weight && item.unit_price ? ` <span class="unit-price-cart">(${escapeHtml(item.unit_price)})</span>` : ''} • Aisle ${escapeHtml(displayAisle)}
                    </div>
                </div>
                <button class="cart-item-delete" onclick="removeFromCart(${index})">×</button>
            </div>
        `;
    });

    cartItems.innerHTML = html;
    cartCount.textContent = totalItems;

    const tax = subtotal * NC_TAX_RATE;
    const total = subtotal + tax;

    document.getElementById('subtotal').textContent = `$${subtotal.toFixed(2)}`;
    document.getElementById('tax').textContent = `$${tax.toFixed(2)}`;
    document.getElementById('total').textContent = `$${total.toFixed(2)}`;
    document.getElementById('cartTotals').style.display = 'block';
    document.getElementById('exportBtn').style.display = 'block';
    document.getElementById('printListBtn').style.display = 'block';
    document.getElementById('saveCustomBtn').style.display = 'block';

    console.log('✅ Cart rendered:', totalItems, 'items, $' + total.toFixed(2), 'total');
}

async function updateQuantity(index, newQty) {
    const item = cart[index];
    const qty = parseFloat(newQty);

    if (qty < 0.1) {
        showToast('Quantity must be at least 0.1', true);
        renderCart();
        return;
    }

    try {
        const response = await auth.fetchWithAuth('/api/cart/quantity', {
            method: 'PUT',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                cart_item_id: item.id,
                quantity: qty
            })
        });

        const data = await response.json();
        cart = data.cart;
        renderCart();

        // AUTO-SAVE after cart change
        scheduleAutoSave();

    } catch (error) {
        showToast('Failed to update quantity', true);
        console.error('Update quantity error:', error);
        renderCart();
    }
}

// Delete modal state
let itemIndexToDelete = null;

function removeFromCart(index) {
    // Show confirmation modal instead of directly removing
    itemIndexToDelete = index;
    const item = cart[index];

    // Handle field name differences
    const displayName = item.product_name || item.name;

    document.getElementById('deleteMessage').textContent =
        `Remove "${displayName}" from your cart?`;

    openModal('deleteModal');
}

function closeDeleteModal() {
    closeModal('deleteModal');
    itemIndexToDelete = null;
}

async function confirmDelete() {
    if (itemIndexToDelete !== null) {
        const item = cart[itemIndexToDelete];
        const itemName = item.product_name || item.name;
        const cartItemId = item.id;

        // Close modal immediately
        closeModal('deleteModal');

        try {
            const response = await auth.fetchWithAuth(`/api/cart/${cartItemId}`, {
                method: 'DELETE'
            });

            const data = await response.json();
            cart = data.cart;
            renderCart();

            // AUTO-SAVE after cart change
            scheduleAutoSave();

            showToast('✓ Item removed');
            console.log('🗑️ Removed:', itemName);
        } catch (error) {
            showToast('Failed to remove item', true);
            console.error('Remove error:', error);
        }
    }

    closeDeleteModal();
}

async function clearCart() {
    if (cart.length === 0) return;
    openModal('clearCartButtonModal');
}

async function confirmClearCart() {
    closeModal('clearCartButtonModal');

    try {
        const response = await auth.fetchWithAuth('/api/cart', {
            method: 'DELETE'
        });

        const data = await response.json();
        cart = data.cart;
        renderCart();
        showToast('✓ Cart cleared');
    } catch (error) {
        showToast('Failed to clear cart', true);
        console.error('Clear cart error:', error);
    }
}

// Cart is now managed by server - this function is deprecated but kept for backwards compatibility
function saveCart() {
    // No-op: cart is saved automatically via API calls
    console.log('ℹ️  Cart is managed by server');
}

function viewFinalList() {
    if (cart.length === 0) return;

    // Organize by aisle
    const byAisle = {};
    cart.forEach(item => {
        const aisle = item.aisle;
        if (!byAisle[aisle]) byAisle[aisle] = [];
        byAisle[aisle].push(item);
    });

    const sortedAisles = Object.keys(byAisle).sort((a, b) => {
        const aNum = parseInt(a.match(/\d+/)?.[0] || '999');
        const bNum = parseInt(b.match(/\d+/)?.[0] || '999');
        return aNum - bNum;
    });

    let subtotal = 0;
    let totalItems = 0;

    let html = '<table><thead><tr><th>Aisle</th><th>Qty</th><th>Product</th><th>Price</th><th>Subtotal</th></tr></thead><tbody>';

    sortedAisles.forEach(aisle => {
        byAisle[aisle].forEach(item => {
            const qty = item.quantity;

            // Handle both string ("$2.49") and number (2.49) from database
            const price = typeof item.price === 'string'
                ? parseFloat(item.price.replace('$', ''))
                : parseFloat(item.price);
            const itemSubtotal = price * qty;
            subtotal += itemSubtotal;
            totalItems += qty;

            // Handle field name differences (database vs local)
            const displayName = item.product_name || item.name;
            const displayPrice = typeof item.price === 'number' ? `$${item.price.toFixed(2)}` : item.price;

            html += `
                <tr>
                    <td><strong>${escapeHtml(aisle)}</strong></td>
                    <td>${qty}x</td>
                    <td>${escapeHtml(displayName)}</td>
                    <td>${escapeHtml(displayPrice)}</td>
                    <td>$${itemSubtotal.toFixed(2)}</td>
                </tr>
            `;
        });
    });

    const tax = subtotal * NC_TAX_RATE;
    const total = subtotal + tax;

    html += `
        <tr class="total-row">
            <td colspan="4" class="text-right">Subtotal:</td>
            <td>$${subtotal.toFixed(2)}</td>
        </tr>
        <tr class="total-row">
            <td colspan="4" class="text-right">Tax (4%):</td>
            <td>$${tax.toFixed(2)}</td>
        </tr>
        <tr class="grand-total-row">
            <td colspan="4" class="text-right">TOTAL:</td>
            <td>$${total.toFixed(2)}</td>
        </tr>
    `;

    html += '</tbody></table>';
    html += `<p class="mt-5 text-secondary"><strong>${totalItems} total items</strong> • Food taxed at 2%, non-food at 7.25% in NC</p>`;

    document.getElementById('finalListTable').innerHTML = html;
    openModal('finalListModal');
}

function closeFinalList() {
    closeModal('finalListModal');
}

function generateMarkdown() {
    const byAisle = {};
    cart.forEach(item => {
        const aisle = item.aisle;
        if (!byAisle[aisle]) byAisle[aisle] = [];
        byAisle[aisle].push(item);
    });

    const sortedAisles = Object.keys(byAisle).sort((a, b) => {
        const aNum = parseInt(a.match(/\d+/)?.[0] || '999');
        const bNum = parseInt(b.match(/\d+/)?.[0] || '999');
        return aNum - bNum;
    });

    let subtotal = 0;
    let totalItems = 0;
    let markdown = '# Wegmans Shopping List - Raleigh, NC\n\n';
    markdown += '| Aisle | Qty | Product | Price | Subtotal |\n';
    markdown += '|-------|-----|---------|-------|----------|\n';

    sortedAisles.forEach(aisle => {
        byAisle[aisle].forEach(item => {
            const qty = item.quantity;

            // Handle both string ("$2.49") and number (2.49) from database
            const price = typeof item.price === 'string'
                ? parseFloat(item.price.replace('$', ''))
                : parseFloat(item.price);
            const itemSubtotal = price * qty;
            subtotal += itemSubtotal;
            totalItems += qty;

            // Handle field name differences
            const displayName = item.product_name || item.name;
            const displayPrice = typeof item.price === 'number' ? `$${item.price.toFixed(2)}` : item.price;

            markdown += `| **${aisle}** | ${qty}x | ${displayName} | ${displayPrice} | $${itemSubtotal.toFixed(2)} |\n`;
        });
    });

    const tax = subtotal * NC_TAX_RATE;
    const total = subtotal + tax;

    markdown += `| | | **Subtotal** | | **$${subtotal.toFixed(2)}** |\n`;
    markdown += `| | | **Tax (4%)** | | **$${tax.toFixed(2)}** |\n`;
    markdown += `| | | **TOTAL** | | **$${total.toFixed(2)}** |\n\n`;
    markdown += `*${totalItems} total items • Food taxed at 2%, non-food at 7.25% in NC*\n`;

    return markdown;
}

function copyMarkdown() {
    const markdown = generateMarkdown();
    navigator.clipboard.writeText(markdown).then(() => {
        showToast('✓ Copied to clipboard!');
    }).catch(() => {
        showToast('Failed to copy', true);
    });
}

function downloadMarkdown() {
    const markdown = generateMarkdown();
    const blob = new Blob([markdown], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'wegmans_shopping_list.md';
    a.click();
    showToast('✓ Downloaded!');
}

// ==================== SAVED LISTS MANAGEMENT ====================

// Deprecated: Lists are now stored in database
function getSavedLists() {
    console.warn('⚠️ getSavedLists() is deprecated - use showPastLists() API call instead');
    return [];
}

function saveSavedLists(lists) {
    console.warn('⚠️ saveSavedLists() is deprecated - lists are stored in database');
}

async function saveCurrentList() {
    const listName = document.getElementById('saveListName').value.trim();
    if (!listName) {
        showToast('Please enter a list name', true);
        return;
    }

    if (cart.length === 0) {
        showToast('Cart is empty!', true);
        return;
    }

    try {
        // Save to database via API
        const response = await auth.fetchWithAuth('/api/lists/save', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ name: listName })
        });

        const data = await response.json();

        if (data.success) {
            document.getElementById('saveListName').value = '';

            // Update frequent items in database (WITHOUT clearing cart)
            try {
                await auth.fetchWithAuth('/api/cart/update-frequent', {
                    method: 'POST'
                });
                console.log('✅ Updated frequent items in database');
            } catch (e) {
                console.warn('Failed to update frequent items:', e);
            }

            showToast(`✓ Saved "${listName}"!`);

            // Refresh frequently bought items display
            loadFrequentItems();

            // Cart remains intact - user can save multiple times or clear manually
        } else {
            showToast('Failed to save list', true);
        }
    } catch (error) {
        console.error('Save list error:', error);
        showToast('Failed to save list', true);
    }
}

function calculateTotal() {
    let subtotal = 0;
    cart.forEach(item => {
        // Handle both string ("$2.49") and number (2.49) from database
        const price = typeof item.price === 'string'
            ? parseFloat(item.price.replace('$', ''))
            : parseFloat(item.price);
        subtotal += price * item.quantity;
    });
    const tax = subtotal * NC_TAX_RATE;
    return subtotal + tax;
}

async function showPastLists() {
    const container = document.getElementById('savedListsContainer');

    try {
        // Fetch lists from database API
        const response = await auth.fetchWithAuth('/api/lists');
        const data = await response.json();
        const lists = data.lists || [];

        if (lists.length === 0) {
            container.innerHTML = '<div class="empty-cart"><div class="emoji"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="48" height="48"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"></path><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"></path></svg></div><p style="font-weight: 600; color: var(--text-primary); margin-bottom: var(--space-2);">No saved lists yet</p><p class="text-xs">Complete a shopping list and save it to see it here!</p></div>';
        } else {
            // Simple two-category system:
            // 1. Custom saved lists (is_auto_saved=FALSE) - User-named lists
            // 2. Shopping history (is_auto_saved=TRUE) - Auto-saved date lists
            const customLists = lists.filter(l => !l.is_auto_saved);
            const shoppingHistory = lists.filter(l => l.is_auto_saved);

            let html = '';

            // Show custom lists first (most important)
            if (customLists.length > 0) {
                html += '<h3 style="margin: 0 0 var(--space-4) 0; padding: var(--space-3); background: var(--primary-wegmans); color: var(--white); border-radius: var(--radius-md); font-size: var(--font-size-sm); font-weight: var(--font-weight-semibold); text-transform: uppercase; letter-spacing: 0.5px;">⭐ My Custom Lists</h3>';
                customLists.forEach(list => {
                    html += renderListCard(list);
                });
            }

            // Show shopping history second
            if (shoppingHistory.length > 0) {
                html += '<h3 style="margin: var(--space-8) 0 var(--space-4) 0; padding: var(--space-3); background: var(--gray-100); border-radius: var(--radius-md); color: var(--text-secondary); font-size: var(--font-size-sm); font-weight: var(--font-weight-semibold); text-transform: uppercase; letter-spacing: 0.5px;">📅 Shopping History</h3>';
                shoppingHistory.forEach(list => {
                    html += renderListCard(list);
                });
            }

            container.innerHTML = html;
        }

        openModal('savedListsModal');
    } catch (error) {
        console.error('Error loading past lists:', error);
    }
}

function renderListCard(list) {
    const date = new Date(list.created_at);
    const dateStr = date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });

    // Display list name (custom lists show user name, auto-saved show date)
    const displayName = list.name;
    const subtitle = dateStr;

    let html = `
        <div class="saved-list-item">
            <div class="saved-list-header">
                <div class="saved-list-name">${escapeHtml(displayName)}</div>
                <div class="saved-list-date">${escapeHtml(subtitle)}</div>
            </div>
            <div class="saved-list-meta">
                ${list.items.length} unique items • ${list.total_quantity} total • $${list.total_price.toFixed(2)}
            </div>

            <div class="saved-list-items-preview">
    `;

    // Show individual items with quick-add buttons
    list.items.forEach((item, index) => {
        // Handle database field names
        const itemData = {
            name: item.product_name,
            price: typeof item.price === 'number' ? `$${item.price.toFixed(2)}` : item.price,
            aisle: item.aisle,
            image: item.image_url,
            search_term: item.search_term || 'saved',
            is_sold_by_weight: item.is_sold_by_weight || false,
            unit_price: item.unit_price || null
        };

        const displayPrice = typeof item.price === 'number' ? `$${item.price.toFixed(2)}` : item.price;

        html += `
            <div class="saved-list-item-row">
                <div class="saved-list-item-info">
                    <span class="saved-list-item-qty">${item.quantity}×</span>
                    <span class="saved-list-item-name">${escapeHtml(item.product_name)}</span>
                    <span style="color: var(--text-secondary);">${escapeHtml(displayPrice)}</span>
                </div>
                <button class="saved-list-item-add" onclick='showQuantityModal(${JSON.stringify(itemData)})'>
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" style="display: inline-block; vertical-align: middle; margin-right: 4px;">
                        <line x1="12" y1="5" x2="12" y2="19"></line>
                        <line x1="5" y1="12" x2="19" y2="12"></line>
                    </svg>
                    Add
                </button>
            </div>
        `;
    });

    html += `
            </div>

            <div class="saved-list-actions">
                <button class="btn-load-all" onclick="replaceCartWithList(${list.id})" style="background: var(--primary-red); color: var(--white);">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="display: inline-block; vertical-align: middle; margin-right: 4px;">
                        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                        <polyline points="7 10 12 15 17 10"></polyline>
                        <line x1="12" y1="15" x2="12" y2="3"></line>
                    </svg>
                    Load This List
                </button>
                <button class="btn-load-all" onclick="addListToCart(${list.id})">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="display: inline-block; vertical-align: middle; margin-right: 4px;">
                        <line x1="12" y1="5" x2="12" y2="19"></line>
                        <line x1="5" y1="12" x2="19" y2="12"></line>
                    </svg>
                    Add to Current
                </button>
                <button class="btn-delete-list" onclick="deleteSavedList(${list.id})">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="display: inline-block; vertical-align: middle; margin-right: 4px;">
                        <polyline points="3 6 5 6 21 6"></polyline>
                        <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                    </svg>
                    Delete
                </button>
            </div>
        </div>
    `;

    return html;
}


function closeSavedLists() {
    closeModal('savedListsModal');
}

async function replaceCartWithList(listId) {
    try {
        console.log('📋 Loading list from database:', listId);

        // Call API to load list (replaces current cart)
        const response = await auth.fetchWithAuth(`/api/lists/${listId}/load`, {
            method: 'POST'
        });

        if (!response.ok) {
            throw new Error(`Failed to load list: ${response.status}`);
        }

        const data = await response.json();

        if (data.success) {
            // Update cart from server response
            cart = data.cart || [];
            renderCart();
            closeSavedLists();
            showToast(`✓ Loaded "${data.list_name}" (${cart.length} items)`);
        } else {
            showToast('Failed to load list', true);
        }
    } catch (error) {
        console.error('Error loading list:', error);
        showToast('Failed to load list', true);
    }
}

async function addListToCart(listId) {
    try {
        console.log('➕ Adding list items to current cart from database:', listId);

        // First fetch the list details
        const response = await auth.fetchWithAuth('/api/lists');
        const data = await response.json();
        const lists = data.lists || [];
        const list = lists.find(l => l.id === listId);

        if (!list) {
            showToast('List not found', true);
            return;
        }

        // Add items from saved list to current cart via API
        let addedCount = 0;
        for (const savedItem of list.items) {
            try {
                const addResponse = await auth.fetchWithAuth('/api/cart/add', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        name: savedItem.product_name,
                        price: typeof savedItem.price === 'number' ? `$${savedItem.price.toFixed(2)}` : savedItem.price,
                        quantity: savedItem.quantity,
                        aisle: savedItem.aisle,
                        image: savedItem.image_url,
                        search_term: savedItem.search_term || 'saved',
                        is_sold_by_weight: savedItem.is_sold_by_weight || false,
                        unit_price: savedItem.unit_price || null
                    })
                });

                const addData = await addResponse.json();
                cart = addData.cart;
                addedCount++;
            } catch (error) {
                console.error('Error adding item:', savedItem.product_name, error);
            }
        }

        renderCart();
        closeSavedLists();
        showToast(`✓ Added ${addedCount} items to cart`);
    } catch (error) {
        console.error('Error adding list to cart:', error);
        showToast('Failed to add list to cart', true);
    }
}

async function deleteSavedList(listId) {
    try {
        // First fetch the list to get its name for confirmation
        const response = await auth.fetchWithAuth('/api/lists');
        const data = await response.json();
        const lists = data.lists || [];
        const list = lists.find(l => l.id === listId);

        if (!list) {
            showToast('List not found', true);
            return;
        }

        // Store list ID for confirmation and show modal
        window.listToDelete = listId;
        document.getElementById('deleteListMessage').textContent = `Are you sure you want to delete "${list.name}"?`;
        openModal('deleteListModal');
    } catch (error) {
        console.error('Error preparing to delete list:', error);
        showToast('Failed to delete list', true);
    }
}

async function confirmDeleteList() {
    closeModal('deleteListModal');
    const listId = window.listToDelete;

    if (!listId) return;

    try {
        console.log('🗑️ Deleting list from database:', listId);

        // Call API to delete list
        const deleteResponse = await auth.fetchWithAuth(`/api/lists/${listId}`, {
            method: 'DELETE'
        });

        if (!deleteResponse.ok) {
            throw new Error(`Failed to delete list: ${deleteResponse.status}`);
        }

        const deleteData = await deleteResponse.json();

        if (deleteData.success) {
            showPastLists(); // Refresh display
            showToast('✓ List deleted');

            // Refresh frequently bought items
            loadFrequentItems();
        } else {
            showToast('Failed to delete list', true);
        }
    } catch (error) {
        console.error('Error deleting list:', error);
        showToast('Failed to delete list', true);
    }
}

// Cart toggle for mobile
function toggleCart() {
    const cartSection = document.querySelector('.cart-section');
    const toggleIcon = document.getElementById('cartToggleIcon');
    
    cartSection.classList.toggle('collapsed');
    
    console.log(cartSection.classList.contains('collapsed') ? '📦 Cart collapsed' : '📦 Cart expanded');
}

// Initialize cart as collapsed on mobile
if (window.innerWidth <= 767) {
    document.addEventListener('DOMContentLoaded', () => {
        const cartSection = document.querySelector('.cart-section');
        if (cartSection) {
            cartSection.classList.add('collapsed');
            console.log('📱 Mobile detected - Cart starts collapsed');
        }
    });
}

// ===== PRINT FUNCTIONALITY =====

async function printShoppingList() {
    if (cart.length === 0) {
        showToast('Cart is empty!', true);
        return;
    }

    // Show loading state
    showToast('⏳ Preparing your list...', false);

    try {
        // 1. Auto-save one final time
        await autoSaveCart();

        // 2. Update frequent items (for future recommendations)
        await auth.fetchWithAuth('/api/cart/update-frequent', { method: 'POST' });

        // 3. Generate print content
        const { html, styles } = generatePrintableList();

        // Create or get print container
        let printDiv = document.getElementById('printable-content');
        if (!printDiv) {
            printDiv = document.createElement('div');
            printDiv.id = 'printable-content';
            printDiv.className = 'print-only';
            document.body.appendChild(printDiv);
        }

        // Inject styles if not already present
        if (!document.getElementById('print-styles-injected')) {
            const styleEl = document.createElement('style');
            styleEl.id = 'print-styles-injected';
            styleEl.textContent = `
                /* Hide everything except print content when printing */
                @media print {
                    body > *:not(.print-only) {
                        display: none !important;
                    }
                    .print-only {
                        display: block !important;
                    }
                }
                /* Hide print content on screen */
                @media screen {
                    .print-only {
                        display: none !important;
                    }
                }
                /* Print-specific styles */
                @media print {
                    ${styles}
                }
            `;
            document.head.appendChild(styleEl);
        }

        // Set print content
        printDiv.innerHTML = html;

        // Setup afterprint handler to fix mobile zoom
        const afterPrintHandler = () => {
            // Fix mobile zoom issue after printing
            if (window.innerWidth <= 767) {
                // Force viewport reset
                const viewport = document.querySelector('meta[name=viewport]');
                if (viewport) {
                    const content = viewport.getAttribute('content');
                    viewport.setAttribute('content', 'width=device-width, initial-scale=1.0, maximum-scale=1.0');
                    // Reset back to allow zoom after a moment
                    setTimeout(() => {
                        viewport.setAttribute('content', content);
                    }, 100);
                }
            }
            window.removeEventListener('afterprint', afterPrintHandler);
        };
        window.addEventListener('afterprint', afterPrintHandler, { once: true });

        // Print immediately
        window.print();

    } catch (error) {
        console.error('Print error:', error);
        showToast('Failed to prepare list', true);
    }
}


function getMobilePrintStyles() {
    return `
        * { margin: 0; padding: 0; box-sizing: border-box; }
        @page { margin: 0.2in; size: portrait; }
        body { font-family: Arial, sans-serif; padding: 3px; font-size: 9px; line-height: 1.1; background: white; }
        h1 { color: #ce3f24; font-size: 12px; margin-bottom: 1px; padding-bottom: 1px; border-bottom: 1px solid #ce3f24; }
        h2 { color: #333; font-size: 8px; font-weight: 600; margin: 2px 0 1px 0; padding: 1px 0 1px 3px; border-left: 2px solid #ce3f24; background: white; }
        .meta { color: #666; font-size: 7px; margin-bottom: 2px; line-height: 1.1; }
        table { width: 100%; border-collapse: collapse; margin-top: 0; table-layout: fixed; }
        th { background: white; text-align: left; padding: 1px 2px; border-bottom: 1px solid #ddd; font-size: 7px; }
        th:first-child { width: 20px; } /* Checkbox column */
        th:nth-child(2) { width: 35px; } /* Qty column */
        th:last-child { width: 55px; } /* Price column */
        td { padding: 1px 2px; border-bottom: 1px solid #f0f0f0; font-size: 9px; line-height: 1.1; vertical-align: top; }
        td:first-child { width: 20px; text-align: center; } /* Checkbox */
        td:nth-child(2) { width: 35px; text-align: center; font-weight: bold; } /* Qty */
        td:last-child { width: 55px; text-align: right; } /* Price */
        tr { page-break-inside: avoid; }
        .checkbox { width: 8px; height: 8px; border: 1px solid #999; display: inline-block; vertical-align: middle; }
        .totals { margin-top: 3px; text-align: right; font-size: 9px; background: white; }
        .totals div { padding: 0; line-height: 1.2; }
        .grand-total { font-weight: bold; font-size: 10px; color: #ce3f24; border-top: 1px solid #333; padding-top: 2px; margin-top: 2px; }
    `;
}

function getDesktopPrintStyles() {
    return `
        * { margin: 0; padding: 0; box-sizing: border-box; }
        @page { margin: 0.4in; }
        body { font-family: Arial, sans-serif; max-width: 8in; margin: 0 auto; padding: 12px; font-size: 11px; background: white; }
        h1 { color: #ce3f24; border-bottom: 2px solid #ce3f24; padding-bottom: 4px; margin-bottom: 8px; font-size: 20px; }
        h2 { color: #333; margin: 12px 0 4px 0; border-bottom: 1px solid #ccc; padding-bottom: 2px; font-size: 13px; background: white; }
        .meta { color: #666; font-size: 10px; margin-bottom: 12px; line-height: 1.3; }
        table { width: 100%; border-collapse: collapse; margin-top: 4px; table-layout: fixed; }
        th { background: white; text-align: left; padding: 4px 6px; border-bottom: 1px solid #ccc; font-size: 10px; }
        th:first-child { width: 30px; } /* Checkbox column */
        th:nth-child(2) { width: 50px; } /* Qty column */
        th:last-child { width: 70px; } /* Price column */
        td { padding: 3px 6px; border-bottom: 1px solid #eee; font-size: 11px; vertical-align: top; }
        td:first-child { width: 30px; text-align: center; } /* Checkbox */
        td:nth-child(2) { width: 50px; text-align: center; font-weight: bold; } /* Qty */
        td:last-child { width: 70px; text-align: right; } /* Price */
        tr { page-break-inside: avoid; }
        .checkbox { width: 14px; height: 14px; border: 2px solid #999; display: inline-block; vertical-align: middle; }
        .totals { margin-top: 12px; text-align: right; font-size: 12px; background: white; }
        .totals div { padding: 2px 0; }
        .grand-total { font-weight: bold; font-size: 14px; color: #ce3f24; border-top: 2px solid #333; padding-top: 6px; margin-top: 6px; }
    `;
}

function isMobileDevice() {
    const ua = navigator.userAgent.toLowerCase();
    return /iphone|ipod|android/.test(ua) && !/ipad|tablet/.test(ua);
}

function generatePrintableList() {
    const listName = getTodaysListName();
    const date = new Date().toLocaleDateString();
    const isMobile = isMobileDevice();

    // Organize by aisle
    const byAisle = {};
    cart.forEach(item => {
        const aisle = item.aisle || 'Unknown';
        if (!byAisle[aisle]) byAisle[aisle] = [];
        byAisle[aisle].push(item);
    });

    // Calculate totals
    let subtotal = 0;
    cart.forEach(item => {
        const price = typeof item.price === 'number' ? item.price : parseFloat(item.price.replace('$', ''));
        subtotal += price * item.quantity;
    });
    const tax = subtotal * NC_TAX_RATE;
    const total = subtotal + tax;

    // Generate mobile-specific or desktop styles
    const styles = isMobile ? getMobilePrintStyles() : getDesktopPrintStyles();

    // Generate HTML for print (body content only, no style tag)
    let html = `
        <h1>${isMobile ? 'Wegmans Shopping List' : '🛒 Wegmans Shopping List'}</h1>
            <div class="meta">
                <strong>${listName}</strong><br>
                Printed: ${date}<br>
                ${cart.length} unique items • ${cart.reduce((sum, i) => sum + i.quantity, 0)} total items
            </div>
    `;

    // Group items by aisle
    const sortedAisles = Object.keys(byAisle).sort();

    sortedAisles.forEach(aisle => {
        html += `<h2>Aisle: ${aisle}</h2><table>`;
        html += `<tr><th>☐</th><th>Qty</th><th>Product</th><th>Price</th></tr>`;

        byAisle[aisle].forEach(item => {
            const name = item.product_name || item.name;
            const price = typeof item.price === 'number' ? `$${item.price.toFixed(2)}` : item.price;

            // Format quantity with units for weight items
            let qtyDisplay;
            if (item.is_sold_by_weight) {
                const unit = item.sell_by_unit || 'lb';
                const unitPlural = getPluralUnit(unit);
                qtyDisplay = `${item.quantity} ${unitPlural}`;
            } else {
                qtyDisplay = `${item.quantity}×`;
            }

            html += `
                <tr>
                    <td><span class="checkbox"></span></td>
                    <td class="qty">${qtyDisplay}</td>
                    <td>${escapeHtml(name)}</td>
                    <td class="price">${price}</td>
                </tr>
            `;
        });

        html += `</table>`;
    });

    // Totals
    html += `
        <div class="totals">
            <div>Subtotal: $${subtotal.toFixed(2)}</div>
            <div>Est. Tax (${(NC_TAX_RATE * 100).toFixed(0)}%): $${tax.toFixed(2)}</div>
            <div class="grand-total">Total: $${total.toFixed(2)}</div>
        </div>

    `;

    return { html, styles };
}

// ===== SAVE CUSTOM LIST =====

async function saveCustomListNow() {
    const listName = document.getElementById('customListName').value.trim();
    if (!listName) {
        showToast('Please enter a list name', true);
        return;
    }

    if (cart.length === 0) {
        showToast('Cart is empty!', true);
        return;
    }

    // Close modal immediately (optimistic UI)
    document.getElementById('customListName').value = '';
    closeModal('saveListModal');
    showToast(`💾 Saving "${listName}"...`);

    try {
        // Create NEW custom list (not tagging - creates separate list)
        const response = await auth.fetchWithAuth('/api/lists/save', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ name: listName })
        });

        const data = await response.json();

        if (data.success) {
            showToast(`✓ Saved "${listName}"!`);
            // Note: Cart remains for continued shopping
        } else {
            showToast('Failed to save list', true);
        }
    } catch (error) {
        showToast('Failed to save list', true);
        console.error('Save error:', error);
    }
}

// ===== RECIPE MANAGEMENT =====

let currentRecipeItems = []; // For interactive add flow
let currentRecipeItemIndex = 0;

async function showRecipes() {
    const container = document.getElementById('recipesContainer');

    try {
        // Fetch recipes from database API
        const response = await auth.fetchWithAuth('/api/recipes');
        const data = await response.json();
        const recipes = data.recipes || [];

        if (recipes.length === 0) {
            container.innerHTML = '<div class="empty-cart"><div class="emoji"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="48" height="48"><path d="M12 2l3 9h9l-7.5 5.5L19 25l-7-5-7 5 2.5-8.5L0 11h9z"></path></svg></div><p style="font-weight: 600; color: var(--text-primary); margin-bottom: var(--space-2);">No recipes yet</p><p class="text-xs">Save your cart as a recipe or create a new one!</p></div>';
        } else {
            let html = '';
            recipes.forEach(recipe => {
                html += renderRecipeCard(recipe);
            });
            container.innerHTML = html;
        }

        openModal('recipesModal');
    } catch (error) {
        console.error('Error loading recipes:', error);
    }
}

function renderRecipeCard(recipe) {
    const date = new Date(recipe.created_at);
    const dateStr = date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });

    let html = `
        <div class="saved-list-item">
            <div class="saved-list-header">
                <div class="saved-list-name">${escapeHtml(recipe.name)}</div>
                <div class="saved-list-date">${recipe.description ? escapeHtml(recipe.description) : dateStr}</div>
            </div>
            <div class="saved-list-meta">
                ${recipe.items.length} items • ${recipe.total_quantity} total • $${recipe.total_price.toFixed(2)}
            </div>

            <div class="saved-list-items-preview">
    `;

    // Show individual items
    recipe.items.forEach((item, index) => {
        const itemData = {
            name: item.product_name,
            price: typeof item.price === 'number' ? `$${item.price.toFixed(2)}` : item.price,
            aisle: item.aisle,
            image: item.image_url,
            search_term: item.search_term || 'recipe',
            is_sold_by_weight: item.is_sold_by_weight || false,
            unit_price: item.unit_price || null
        };

        const displayPrice = typeof item.price === 'number' ? `$${item.price.toFixed(2)}` : item.price;

        html += `
            <div class="saved-list-item-row">
                <div class="saved-list-item-info">
                    <span class="saved-list-item-qty">${item.quantity}×</span>
                    <span class="saved-list-item-name">${escapeHtml(item.product_name)}</span>
                    <span style="color: var(--text-secondary);">${escapeHtml(displayPrice)}</span>
                </div>
            </div>
        `;
    });

    html += `
            </div>

            <div class="saved-list-actions">
                <button class="btn-load-all" onclick="addAllRecipeItems(${recipe.id})" style="background: var(--primary-red); color: var(--white);">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="display: inline-block; vertical-align: middle; margin-right: 4px;">
                        <line x1="12" y1="5" x2="12" y2="19"></line>
                        <line x1="5" y1="12" x2="19" y2="12"></line>
                    </svg>
                    Add All
                </button>
                <button class="btn-load-all" onclick="startInteractiveAdd(${recipe.id})">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="display: inline-block; vertical-align: middle; margin-right: 4px;">
                        <circle cx="12" cy="12" r="10"></circle>
                        <line x1="12" y1="8" x2="12" y2="16"></line>
                        <line x1="8" y1="12" x2="16" y2="12"></line>
                    </svg>
                    Interactive Add
                </button>
                <button class="btn-delete-list" onclick="deleteRecipe(${recipe.id})">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="display: inline-block; vertical-align: middle; margin-right: 4px;">
                        <polyline points="3 6 5 6 21 6"></polyline>
                        <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                    </svg>
                    Delete
                </button>
            </div>
        </div>
    `;

    return html;
}

async function saveCartAsRecipe() {
    if (cart.length === 0) {
        showToast('Cart is empty!', true);
        return;
    }

    openModal('saveRecipeModal');
}

async function confirmSaveRecipe() {
    const name = document.getElementById('recipeNameInput').value.trim();
    const description = document.getElementById('recipeDescriptionInput').value.trim();

    if (!name) {
        showToast('Please enter a recipe name', true);
        return;
    }

    // Clear form and close modal immediately (optimistic UI)
    document.getElementById('recipeNameInput').value = '';
    document.getElementById('recipeDescriptionInput').value = '';
    closeModal('saveRecipeModal');
    showToast(`✓ Saving recipe "${name}"...`);

    try {
        const response = await auth.fetchWithAuth('/api/recipes/save-cart', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ name, description: description || null })
        });

        const data = await response.json();

        if (data.success) {
            showToast(`✓ Recipe "${name}" saved!`);
        } else {
            showToast('Failed to save recipe', true);
        }
    } catch (error) {
        console.error('Save recipe error:', error);
        showToast('Failed to save recipe', true);
    }
}

async function addAllRecipeItems(recipeId) {
    try {
        const response = await auth.fetchWithAuth(`/api/recipes/${recipeId}/add-to-cart`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ item_ids: null }) // null = add all
        });

        const data = await response.json();

        if (data.success) {
            cart = data.cart;
            renderCart();
            scheduleAutoSave();
            closeModal('recipesModal');
            showToast(`✓ All items added to cart!`);
        } else {
            showToast('Failed to add items', true);
        }
    } catch (error) {
        console.error('Add all recipe items error:', error);
        showToast('Failed to add items', true);
    }
}

async function startInteractiveAdd(recipeId) {
    try {
        // Fetch recipe details
        const response = await auth.fetchWithAuth('/api/recipes');
        const data = await response.json();
        const recipe = data.recipes.find(r => r.id === recipeId);

        if (!recipe || recipe.items.length === 0) {
            showToast('Recipe has no items', true);
            return;
        }

        // Store recipe items and start flow
        currentRecipeItems = recipe.items.map(item => ({
            ...item,
            recipe_id: recipeId
        }));
        currentRecipeItemIndex = 0;

        closeModal('recipesModal');
        showNextRecipeItem();
    } catch (error) {
        console.error('Start interactive add error:', error);
        showToast('Failed to start interactive add', true);
    }
}

function showNextRecipeItem() {
    if (currentRecipeItemIndex >= currentRecipeItems.length) {
        // Done with all items
        showToast(`✓ Finished adding items!`);
        currentRecipeItems = [];
        currentRecipeItemIndex = 0;
        return;
    }

    const item = currentRecipeItems[currentRecipeItemIndex];
    const displayPrice = typeof item.price === 'number' ? `$${item.price.toFixed(2)}` : item.price;

    // Update modal
    document.getElementById('interactiveItemName').textContent = item.product_name;
    document.getElementById('interactiveItemPrice').textContent = displayPrice;
    document.getElementById('interactiveItemQuantity').textContent = `Default: ${item.quantity}×`;
    document.getElementById('interactiveProgress').textContent = `Item ${currentRecipeItemIndex + 1} of ${currentRecipeItems.length}`;

    openModal('interactiveAddModal');
}

async function skipRecipeItem() {
    currentRecipeItemIndex++;
    closeModal('interactiveAddModal');
    showNextRecipeItem();
}

async function addRecipeItemToCart() {
    const item = currentRecipeItems[currentRecipeItemIndex];

    try {
        const response = await auth.fetchWithAuth('/api/cart/add', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                name: item.product_name,
                price: typeof item.price === 'number' ? `$${item.price.toFixed(2)}` : item.price,
                quantity: item.quantity,
                aisle: item.aisle,
                image: item.image_url,
                search_term: item.search_term || 'recipe',
                is_sold_by_weight: item.is_sold_by_weight || false,
                unit_price: item.unit_price || null
            })
        });

        const data = await response.json();
        cart = data.cart;
        renderCart();
        scheduleAutoSave();

        showToast(`✓ Added ${item.product_name}`);

        currentRecipeItemIndex++;
        closeModal('interactiveAddModal');
        showNextRecipeItem();
    } catch (error) {
        console.error('Add recipe item error:', error);
        showToast('Failed to add item', true);
    }
}

async function deleteRecipe(recipeId) {
    // Show confirmation modal
    window.recipeToDelete = recipeId;
    document.getElementById('deleteRecipeMessage').textContent = 'Are you sure you want to delete this recipe?';
    openModal('deleteRecipeModal');
}

async function confirmDeleteRecipe() {
    closeModal('deleteRecipeModal');
    const recipeId = window.recipeToDelete;

    if (!recipeId) return;

    try {
        const response = await auth.fetchWithAuth(`/api/recipes/${recipeId}`, {
            method: 'DELETE'
        });

        const data = await response.json();

        if (data.success) {
            showRecipes(); // Refresh display
            showToast('✓ Recipe deleted');
        } else {
            showToast('Failed to delete recipe', true);
        }
    } catch (error) {
        console.error('Delete recipe error:', error);
        showToast('Failed to delete recipe', true);
    }
}

function closeRecipes() {
    closeModal('recipesModal');
}

// ====== Export to Text Functions ======

function groupByAisle(items) {
    const grouped = {};
    items.forEach(item => {
        const aisle = item.aisle || 'Other';
        if (!grouped[aisle]) {
            grouped[aisle] = [];
        }
        grouped[aisle].push(item);
    });
    return grouped;
}

function calculateTotal() {
    let subtotal = 0;
    cart.forEach(item => {
        const price = typeof item.price === 'string'
            ? parseFloat(item.price.replace('$', ''))
            : parseFloat(item.price);
        subtotal += price * item.quantity;
    });
    const tax = subtotal * NC_TAX_RATE;
    return (subtotal + tax).toFixed(2);
}

function exportToText() {
    if (cart.length === 0) {
        showToast('Your list is empty', true);
        return;
    }

    console.log('📋 Exporting list to text...');

    // Group items by aisle
    const grouped = groupByAisle(cart);

    // Build text format
    let text = `Wegmans Shopping List - ${getTodaysListName()}\n\n`;

    // Add items by aisle
    for (const [aisle, items] of Object.entries(grouped)) {
        text += `${aisle.toUpperCase()}\n`;
        items.forEach(item => {
            const displayName = item.product_name || item.name;
            const displayPrice = typeof item.price === 'number' ? `$${item.price.toFixed(2)}` : item.price;

            text += `* ${displayName} - ${displayPrice}`;

            // Add quantity with units
            if (item.quantity > 1 || item.is_sold_by_weight) {
                if (item.is_sold_by_weight) {
                    const unit = item.sell_by_unit || 'lb';
                    const unitPlural = getPluralUnit(unit);
                    text += ` (${item.quantity} ${unitPlural})`;
                } else {
                    text += ` (qty: ${item.quantity})`;
                }
            }
            text += '\n';
        });
        text += '\n';
    }

    // Add total
    text += `TOTAL: $${calculateTotal()}\n`;
    text += '---\n';
    text += 'Generated by Wegmans Shopping List Builder\n';
    text += 'https://wegmans-shopping.onrender.com';

    // Copy to clipboard with fallback
    copyToClipboard(text);
}

function copyToClipboard(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
        // Modern clipboard API
        navigator.clipboard.writeText(text)
            .then(() => {
                console.log('✅ Copied to clipboard');
                showToast('✓ Copied to clipboard!');
            })
            .catch(err => {
                console.error('Failed to copy:', err);
                fallbackCopyToClipboard(text);
            });
    } else {
        // Fallback for older browsers
        fallbackCopyToClipboard(text);
    }
}

function fallbackCopyToClipboard(text) {
    // Create temporary textarea
    const textarea = document.createElement('textarea');
    textarea.value = text;
    textarea.style.position = 'fixed';
    textarea.style.opacity = '0';
    document.body.appendChild(textarea);

    try {
        textarea.select();
        const successful = document.execCommand('copy');

        if (successful) {
            console.log('✅ Copied to clipboard (fallback method)');
            showToast('✓ Copied to clipboard!');
        } else {
            console.error('Fallback copy failed');
            showToast('Copy failed - please try again', true);
        }
    } catch (err) {
        console.error('Fallback copy error:', err);
        showToast('Copy not supported in this browser', true);
    } finally {
        document.body.removeChild(textarea);
    }
}

// ====== Remove Favorite Confirmation ======

async function confirmRemoveFavorite() {
    closeModal('removeFavoriteModal');

    const data = window.productToUnfavorite;
    if (!data) return;

    const { product, starBtn, starIcon } = data;

    try {
        const response = await auth.fetchWithAuth(`/api/favorites/${encodeURIComponent(product.name)}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            userFavorites.delete(product.name);
            showToast('Removed from favorites');

            // Update UI
            if (starBtn) {
                starBtn.classList.remove('favorited');
                if (starIcon) starIcon.classList.remove('filled');
            }

            // Reload frequent items to update display
            await loadFrequentItems();
        }
    } catch (error) {
        console.error('Failed to remove favorite:', error);
        showToast('Failed to remove favorite', true);
    }

    window.productToUnfavorite = null;
}
