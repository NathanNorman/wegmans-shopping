let cart = [];
const NC_TAX_RATE = 0.04;

console.log('🚀 Wegmans Shopping List Builder initialized');
console.log('📝 Console logging enabled for debugging');

// Load saved cart from API
console.log('💾 Loading saved cart...');
async function loadCart() {
    try {
        const response = await fetch('/api/cart');
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
}
loadCart();

// Load and display frequently bought items
loadFrequentItems();

// Frequently bought items functions
async function loadFrequentItems() {
    console.log('⭐ Loading frequently bought items from database...');

    try {
        const response = await fetch('/api/frequent');
        const data = await response.json();
        const items = data.items || [];

        if (items.length === 0) {
            console.log('  No frequent items found in database');
            return;
        }

        // Filter to only show items bought 2+ times
        const frequentlyBought = items.filter(item => item.purchase_count >= 2);

        if (frequentlyBought.length === 0) {
            console.log('  No items bought 2+ times yet');
            return;
        }

        // Transform database format to match what renderFrequentItems expects
        const frequentItems = frequentlyBought.slice(0, 8).map(item => ({
            product: {
                name: item.product_name,
                price: typeof item.price === 'number' ? `$${item.price.toFixed(2)}` : item.price,
                aisle: item.aisle,
                image: item.image_url,
                is_sold_by_weight: item.is_sold_by_weight || false
            },
            count: item.purchase_count
        }));

        console.log('✅ Found', frequentItems.length, 'frequently bought items (2+ purchases) from database');
        renderFrequentItems(frequentItems);

    } catch (error) {
        console.log('  No frequent items yet (expected on first use)');
    }
}

function renderFrequentItems(frequentItems) {
    const section = document.getElementById('frequentSection');
    const container = document.getElementById('frequentItems');

    let html = '';
    frequentItems.forEach(item => {
        const product = item.product;
        const imageHtml = product.image
            ? `<img src="${escapeHtml(product.image)}" class="frequent-item-image" alt="${escapeHtml(product.name)}" onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';">
               <div class="frequent-item-image-placeholder" style="display: none;">
                   <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="40" height="40">
                       <circle cx="9" cy="21" r="1"></circle>
                       <circle cx="20" cy="21" r="1"></circle>
                       <path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"></path>
                   </svg>
               </div>`
            : `<div class="frequent-item-image-placeholder">
                   <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="40" height="40">
                       <circle cx="9" cy="21" r="1"></circle>
                       <circle cx="20" cy="21" r="1"></circle>
                       <path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"></path>
                   </svg>
               </div>`;

        html += `
            <div class="frequent-item" onclick='showQuantityModal(${JSON.stringify(product)})'>
                ${imageHtml}
                <div class="frequent-item-name">${escapeHtml(product.name)}</div>
                <div class="frequent-item-footer">
                    <span class="frequent-item-price">${escapeHtml(product.price)}</span>
                    <span class="frequent-item-badge" title="Bought ${item.count} times in past lists">${item.count}× bought</span>
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

    // Reset form
    document.getElementById('quantitySlider').value = 1;
    document.getElementById('quantityDisplay').textContent = '1';
    document.getElementById('customQuantityInput').value = '';

    // Show modal
    const modal = document.getElementById('quantityModal');
    modal.classList.add('show');

    // Setup slider listener
    const slider = document.getElementById('quantitySlider');
    slider.oninput = function() {
        document.getElementById('quantityDisplay').textContent = this.value;
        document.getElementById('customQuantityInput').value = ''; // Clear custom input
    };

    // Setup custom input listener
    const customInput = document.getElementById('customQuantityInput');
    customInput.oninput = function() {
        if (this.value) {
            document.getElementById('quantityDisplay').textContent = this.value;
        }
    };

    // ESC and backdrop close
    openModal('quantityModal');
}

function closeQuantityModal() {
    closeModal('quantityModal');
    currentProductForQuantity = null;
}

async function confirmAddQuantity() {
    if (!currentProductForQuantity) return;

    // Get quantity from slider or custom input
    const customQty = parseFloat(document.getElementById('customQuantityInput').value);
    const sliderQty = parseFloat(document.getElementById('quantitySlider').value);
    const quantity = customQty || sliderQty;

    console.log('⚡ Adding to cart with quantity:', quantity, '-', currentProductForQuantity.name);

    // Call API to add to cart
    try {
        const response = await fetch('/api/cart/add', {
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
                unit_price: currentProductForQuantity.unit_price || null
            })
        });

        const data = await response.json();

        // Update cart from server response
        cart = data.cart;
        renderCart();

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
        showToast('✓ Added to cart');
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

    showLoading(`Searching for "${searchTerm}"...`);
    document.getElementById('searchBtn').disabled = true;

    try {
        console.log('📡 Sending search request...');
        const response = await fetch('/api/search', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                search_term: searchTerm,
                max_results: 10
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
        } else {
            console.log('🎉 Displaying', products.length, 'products');
            displayResults(products, searchTerm);
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

        let html = '';
        if (product.image) {
            html += `
                <img src="${escapeHtml(product.image)}"
                     class="product-image"
                     alt="${escapeHtml(product.name)}"
                     onerror="this.onerror=null; this.src='data:image/svg+xml,%3Csvg xmlns=%27http://www.w3.org/2000/svg%27 viewBox=%270 0 24 24%27 fill=%27none%27 stroke=%27%23999%27 stroke-width=%271.5%27%3E%3Ccircle cx=%279%27 cy=%2721%27 r=%271%27/%3E%3Ccircle cx=%2720%27 cy=%2721%27 r=%271%27/%3E%3Cpath d=%27M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6%27/%3E%3C/svg%3E';">
            `;
        } else {
            html += `
                <div class="product-image" style="display: flex; align-items: center; justify-content: center; background: var(--gray-100);">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="60" height="60">
                        <circle cx="9" cy="21" r="1"></circle>
                        <circle cx="20" cy="21" r="1"></circle>
                        <path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"></path>
                    </svg>
                </div>
            `;
        }

        html += `
            <div class="product-name">${escapeHtml(product.name)}</div>
            <div class="product-info">
                <span class="product-price">${escapeHtml(product.price)}</span>
                <span class="product-aisle">${escapeHtml(product.aisle)}</span>
            </div>
        `;

        card.innerHTML = html;
        grid.appendChild(card);
    });

    console.log('✅ Results displayed successfully');
}

function addToCart(product, searchTerm) {
    console.log('🛒 Adding to cart:', product.name);

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
        showToast('✓ Added to cart');
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
        cartItems.innerHTML = '<div class="empty-cart"><div class="emoji"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="48" height="48"><circle cx="9" cy="21" r="1"></circle><circle cx="20" cy="21" r="1"></circle><path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"></path></svg></div><p style="font-weight: 600; color: var(--text-primary); margin-bottom: var(--space-2);">Your cart is empty</p><p class="text-xs">Start searching to add items!</p></div>';
        cartCount.textContent = '0';
        document.getElementById('cartTotals').style.display = 'none';
        viewListBtn.style.display = 'none';
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

        html += `
            <div class="cart-item">
                <input type="number" class="cart-item-qty" value="${qty}" min="1"
                    onchange="updateQuantity(${index}, this.value)">
                <div class="cart-item-details">
                    <div class="cart-item-name">${escapeHtml(displayName)}</div>
                    <div class="cart-item-meta">
                        ${escapeHtml(displayPrice)} • Aisle ${escapeHtml(displayAisle)}
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
    viewListBtn.style.display = 'block';

    console.log('✅ Cart rendered:', totalItems, 'items, $' + total.toFixed(2), 'total');
}

function updateQuantity(index, newQty) {
    const qty = parseInt(newQty);
    if (qty < 1) {
        showToast('Quantity must be at least 1', true);
        renderCart();
        return;
    }
    cart[index].quantity = qty;
    saveCart();
    renderCart();
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

        try {
            const response = await fetch(`/api/cart/${cartItemId}`, {
                method: 'DELETE'
            });

            const data = await response.json();
            cart = data.cart;
            renderCart();
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
    if (!confirm('Clear entire cart?')) return;

    try {
        const response = await fetch('/api/cart', {
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
        const response = await fetch('/api/lists/save', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ name: listName })
        });

        const data = await response.json();

        if (data.success) {
            document.getElementById('saveListName').value = '';

            // Update frequent items in database (WITHOUT clearing cart)
            try {
                await fetch('/api/cart/update-frequent', {
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
        const response = await fetch('/api/lists');
        const data = await response.json();
        const lists = data.lists || [];

        if (lists.length === 0) {
            container.innerHTML = '<div class="empty-cart"><div class="emoji"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="48" height="48"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"></path><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"></path></svg></div><p style="font-weight: 600; color: var(--text-primary); margin-bottom: var(--space-2);">No saved lists yet</p><p class="text-xs">Complete a shopping list and save it to see it here!</p></div>';
        } else {
            let html = '';
            lists.forEach(list => {
                const date = new Date(list.created_at);
                const dateStr = date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });

                html += `
                    <div class="saved-list-item">
                        <div class="saved-list-header">
                            <div class="saved-list-name">${escapeHtml(list.name)}</div>
                            <div class="saved-list-date">${dateStr}</div>
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
            });
            container.innerHTML = html;
        }

        openModal('savedListsModal');
    } catch (error) {
        console.error('Error loading saved lists:', error);
        showToast('Failed to load saved lists', true);
    }
}

function closeSavedLists() {
    closeModal('savedListsModal');
}

async function replaceCartWithList(listId) {
    try {
        console.log('📋 Loading list from database:', listId);

        // Call API to load list (replaces current cart)
        const response = await fetch(`/api/lists/${listId}/load`, {
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
        const response = await fetch('/api/lists');
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
                const addResponse = await fetch('/api/cart/add', {
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
        const response = await fetch('/api/lists');
        const data = await response.json();
        const lists = data.lists || [];
        const list = lists.find(l => l.id === listId);

        if (!list) {
            showToast('List not found', true);
            return;
        }

        if (!confirm(`Delete "${list.name}"?`)) {
            return;
        }

        console.log('🗑️ Deleting list from database:', listId);

        // Call API to delete list
        const deleteResponse = await fetch(`/api/lists/${listId}`, {
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
