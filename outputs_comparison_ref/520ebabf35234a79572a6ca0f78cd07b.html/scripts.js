// Example JavaScript for rotating deals and trending coupons
document.addEventListener("DOMContentLoaded", function() {
    const deals = document.querySelectorAll('.deal-card');
    let currentDealIndex = 0;

    function rotateDeals() {
        deals[currentDealIndex].style.display = 'none';
        currentDealIndex = (currentDealIndex + 1) % deals.length;
        deals[currentDealIndex].style.display = 'block';
    }

    setInterval(rotateDeals, 5000);

    const coupons = document.querySelectorAll('.coupon');
    let currentCouponIndex = 0;

    function rotateCoupons() {
        coupons[currentCouponIndex].style.display = 'none';
        currentCouponIndex = (currentCouponIndex + 1) % coupons.length;
        coupons[currentCouponIndex].style.display = 'block';
    }

    setInterval(rotateCoupons, 5000);
});