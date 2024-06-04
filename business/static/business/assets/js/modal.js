// Select necessary elements
const searchIcon = document.querySelector('.ph-bold ph-magnifying-glass text-2xl');
const searchModal = document.querySelector('.modal-search-block');
const userIcon = document.querySelector('.user-icon');
const loginPopup = userIcon.querySelector('.login-popup');
const wishlistIcon = document.querySelector('.wishlist-icon');
const wishlistModal = document.querySelector('.modal-wishlist-block');
const cartIcon = document.querySelector('.cart-icon');
const cartModal = document.querySelector('.modal-cart-block');

// Search icon and modal
searchIcon.addEventListener('click', () => {
  searchModal.classList.add('show');
});

const closeSearchModal = searchModal.querySelector('.close-btn');
closeSearchModal.addEventListener('click', () => {
  searchModal.classList.remove('show');
});

// Profile icon and login popup
userIcon.addEventListener('click', () => {
  loginPopup.classList.toggle('show');
});

// Wishlist icon and modal
wishlistIcon.addEventListener('click', () => {
  wishlistModal.classList.add('show');
});

const closeWishlistModal = wishlistModal.querySelector('.close-btn');
closeWishlistModal.addEventListener('click', () => {
  wishlistModal.classList.remove('show');
});

// Cart icon and modal
cartIcon.addEventListener('click', () => {
  cartModal.classList.add('show');
});

const closeCartModal = cartModal.querySelector('.close-btn');
closeCartModal.addEventListener('click', () => {
  cartModal.classList.remove('show');
});

// Close modals when clicking outside
document.addEventListener('click', (event) => {
  const isClickInsideSearchModal = searchModal.contains(event.target);
  const isClickInsideLoginPopup = loginPopup.contains(event.target);
  const isClickInsideWishlistModal = wishlistModal.contains(event.target);
  const isClickInsideCartModal = cartModal.contains(event.target);

  if (!isClickInsideSearchModal && searchModal.classList.contains('show')) {
    searchModal.classList.remove('show');
  }

  if (!isClickInsideLoginPopup && !userIcon.contains(event.target)) {
    loginPopup.classList.remove('show');
  }

  if (!isClickInsideWishlistModal && wishlistModal.classList.contains('show')) {
    wishlistModal.classList.remove('show');
  }

  if (!isClickInsideCartModal && cartModal.classList.contains('show')) {
    cartModal.classList.remove('show');
  }
});
