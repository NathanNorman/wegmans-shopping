// Paste this into browser console to add test data with REAL images
const DUMMY_LISTS = [
    {
        id: Date.now() - 864000000,
        name: "Weekly Groceries",
        date: new Date(Date.now() - 864000000).toISOString(),
        items: [
            { name: "Wegmans Vitamin D Milk", price: "$2.49", aisle: "Dairy", quantity: 2, search_term: "milk", image: "https://images.wegmans.com/is/image/wegmanscsprod/58871?eTag=1726576376684" },
            { name: "Wegmans Grade AA Large Eggs, 18 Count", price: "$2.89", aisle: "Dairy", quantity: 1, search_term: "eggs", image: "https://images.wegmans.com/is/image/wegmanscsprod/46155?eTag=1717087581370" },
            { name: "Wegmans French Baguette", price: "$3.50", aisle: "Fresh Bakery", quantity: 1, search_term: "bread", image: "https://images.wegmans.com/is/image/wegmanscsprod/53556?eTag=1717092237284" },
            { name: "Bananas, Sold by the Each", price: "$0.21", aisle: "Produce", quantity: 6, search_term: "banana", image: "https://images.wegmans.com/is/image/wegmanscsprod/92685?eTag=1717104507851" },
            { name: "SIGGIS Protein Pack, Strawberry Acai", price: "$1.49", aisle: "Dairy", quantity: 1, search_term: "yogurt", image: "https://images.wegmans.com/is/image/wegmanscsprod/957091_PrimaryImage?eTag=1757078219211" }
        ],
        itemCount: 11,
        total: 16.06
    },
    {
        id: Date.now() - 432000000,
        name: "Quick Snack Run",
        date: new Date(Date.now() - 432000000).toISOString(),
        items: [
            { name: "Wegmans Grade AA Large Eggs, 18 Count", price: "$2.89", aisle: "Dairy", quantity: 1, search_term: "eggs", image: "https://images.wegmans.com/is/image/wegmanscsprod/46155?eTag=1717087581370" },
            { name: "Wegmans French Baguette", price: "$3.50", aisle: "Fresh Bakery", quantity: 2, search_term: "bread", image: "https://images.wegmans.com/is/image/wegmanscsprod/53556?eTag=1717092237284" },
            { name: "Wegmans Mexican Fancy Shredded Cheese", price: "$1.99", aisle: "Dairy", quantity: 1, search_term: "cheese", image: "https://images.wegmans.com/is/image/wegmanscsprod/33399?eTag=1717086150231" },
            { name: "Wegmans Wavy Potato Chips", price: "$2.49", aisle: "09B", quantity: 2, search_term: "chips", image: "https://images.wegmans.com/is/image/wegmanscsprod/52231?eTag=1717088768990" }
        ],
        itemCount: 6,
        total: 14.35
    },
    {
        id: Date.now() - 172800000,
        name: "Breakfast Essentials",
        date: new Date(Date.now() - 172800000).toISOString(),
        items: [
            { name: "Wegmans Vitamin D Milk", price: "$2.49", aisle: "Dairy", quantity: 1, search_term: "milk", image: "https://images.wegmans.com/is/image/wegmanscsprod/58871?eTag=1726576376684" },
            { name: "Wegmans Grade AA Large Eggs, 18 Count", price: "$2.89", aisle: "Dairy", quantity: 2, search_term: "eggs", image: "https://images.wegmans.com/is/image/wegmanscsprod/46155?eTag=1717087581370" },
            { name: "Wegmans In-Store Fresh Baked Bagel", price: "$1.29", aisle: "Fresh Bakery", quantity: 1, search_term: "bagels", image: "https://images.wegmans.com/is/image/wegmanscsprod/28115?eTag=1717085532712" },
            { name: "Wegmans Original Cream Cheese Bar", price: "$1.69", aisle: "Dairy", quantity: 1, search_term: "cream cheese", image: "https://images.wegmans.com/is/image/wegmanscsprod/94302?eTag=1717104968565" },
            { name: "Wegmans Orange Juice, 100% Juice, Cold Pressed", price: "$4.00", aisle: "Produce", quantity: 1, search_term: "orange juice", image: "https://images.wegmans.com/is/image/wegmanscsprod/59487_PrimaryImage?eTag=1742828469733" }
        ],
        itemCount: 6,
        total: 15.14
    }
];

localStorage.setItem('wegmans_saved_lists', JSON.stringify(DUMMY_LISTS));
console.log('✅ Test data with REAL images added! Reload the page to see it.');
location.reload();
