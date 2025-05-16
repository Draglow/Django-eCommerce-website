$(document).ready(function() {
    // CSRF token setup for AJAX requests
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
    const csrftoken = getCookie('csrftoken');

    $.ajaxSetup({
        beforeSend: function(xhr, settings) {
            if (!/^(GET|HEAD|OPTIONS|TRACE)$/i.test(settings.type) && !this.crossDomain) {
                xhr.setRequestHeader("X-CSRFToken", csrftoken);
            }
        }
    });

    // Add to Cart functionality
    $('.add-to-cart').click(function(e) {
        e.preventDefault();
        const productId = $(this).data('product-id');
        const quantity = $('#quantity-' + productId).val() || 1;

        $.ajax({
            url: '/mainapp/cart/add/',
            type: 'POST',
            data: {
                'product_id': productId,
                'quantity': quantity
            },
            success: function(response) {
                showToast('Success', 'Product added to cart!', 'success');
                updateCartCount(response.cart_count);
            },
            error: function() {
                showToast('Error', 'Failed to add product to cart.', 'danger');
            }
        });
    });

    // Update Cart Item Quantity
    $('.update-quantity').change(function() {
        const itemId = $(this).data('item-id');
        const quantity = $(this).val();

        $.ajax({
            url: '/mainapp/cart/update/',
            type: 'POST',
            data: {
                'item_id': itemId,
                'quantity': quantity
            },
            success: function(response) {
                updateCartTotal(response.cart_total);
                updateCartCount(response.cart_count);
                $(`#item-total-${itemId}`).text(response.item_total);
            },
            error: function() {
                showToast('Error', 'Failed to update quantity.', 'danger');
            }
        });
    });

    // Remove Cart Item
    $('.remove-item').click(function(e) {
        e.preventDefault();
        const itemId = $(this).data('item-id');

        $.ajax({
            url: '/mainapp/cart/remove/',
            type: 'POST',
            data: {
                'item_id': itemId
            },
            success: function(response) {
                $(`#cart-item-${itemId}`).fadeOut(300, function() {
                    $(this).remove();
                });
                updateCartTotal(response.cart_total);
                updateCartCount(response.cart_count);
                
                if (response.cart_count === 0) {
                    $('#cart-items').html('<p>Your cart is empty.</p>');
                }
            },
            error: function() {
                showToast('Error', 'Failed to remove item.', 'danger');
            }
        });
    });

    // Apply Coupon
    $('#apply-coupon').click(function(e) {
        e.preventDefault();
        const code = $('#coupon-code').val();

        $.ajax({
            url: '/mainapp/cart/apply-coupon/',
            type: 'POST',
            data: {
                'code': code
            },
            success: function(response) {
                if (response.valid) {
                    updateCartTotal(response.cart_total);
                    showToast('Success', 'Coupon applied successfully!', 'success');
                    $('#discount-amount').text(response.discount_amount);
                } else {
                    showToast('Error', 'Invalid coupon code.', 'danger');
                }
            },
            error: function() {
                showToast('Error', 'Failed to apply coupon.', 'danger');
            }
        });
    });

    // Helper Functions
    function updateCartCount(count) {
        $('#cart-count').text(count);
    }

    function updateCartTotal(total) {
        $('#cart-total').text(total);
    }

    function showToast(title, message, type) {
        const toast = `
            <div class="toast" role="alert" aria-live="assertive" aria-atomic="true">
                <div class="toast-header bg-${type} text-white">
                    <strong class="me-auto">${title}</strong>
                    <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close"></button>
                </div>
                <div class="toast-body">
                    ${message}
                </div>
            </div>
        `;

        $('.toast-container').append(toast);
        const toastElement = $('.toast').last();
        const bsToast = new bootstrap.Toast(toastElement);
        bsToast.show();

        setTimeout(() => {
            toastElement.remove();
        }, 3000);
    }

    // Dark Mode Toggle
    $('#dark-mode-toggle').change(function() {
        $('body').toggleClass('dark-mode');
        localStorage.setItem('darkMode', $('body').hasClass('dark-mode') ? 'enabled' : 'disabled');
    });

    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Payment Method Selection
    $('.payment-method-radio').change(function() {
        const method = $(this).val();
        $('.payment-details').hide();
        $(`#${method}-details`).fadeIn();
    });

    // Form Validation
    $('form').on('submit', function(e) {
        if (!this.checkValidity()) {
            e.preventDefault();
            e.stopPropagation();
        }
        $(this).addClass('was-validated');
    });

    // Newsletter subscription
    $('.newsletter-form').on('submit', function(e) {
        e.preventDefault();
        e.stopPropagation();
        
        const form = $(this);
        const submitBtn = form.find('button[type="submit"]');
        const emailInput = form.find('input[type="email"]');
        const messageContainer = form.find('.newsletter-message');
        const email = emailInput.val();

        // Disable submit button and show loading state
        submitBtn.prop('disabled', true).html('<i class="fas fa-spinner fa-spin"></i> Subscribing...');

        $.ajax({
            url: form.attr('action'),
            type: 'POST',
            data: {
                'email': email,
                'csrfmiddlewaretoken': form.find('input[name=csrfmiddlewaretoken]').val()
            },
            dataType: 'json',
            success: function(response) {
                let messageHtml = '';
                if (response.status === 'success') {
                    messageHtml = `
                        <div class="card border-0 shadow-lg newsletter-success-card" style="border-radius: 15px; overflow: hidden; animation: fadeInUp 0.5s ease-out;">
                            <div class="card-body p-4">
                                <div class="d-flex align-items-center">
                                    <div class="newsletter-icon-container me-4" style="width: 60px; height: 60px; background-color: rgba(40, 167, 69, 0.1); border-radius: 50%; display: flex; align-items: center; justify-content: center;">
                                        <i class="fas fa-check-circle text-success" style="font-size: 2rem;"></i>
                                    </div>
                                    <div>
                                        <h5 class="card-title mb-2 fw-bold">Thank You!</h5>
                                        <p class="card-text mb-0 text-muted">${response.message}</p>
                                    </div>
                                </div>
                            </div>
                        </div>`;
                    emailInput.val(''); // Clear the input on success
                } else if (response.status === 'info') {
                    messageHtml = `
                        <div class="card border-0 shadow-lg newsletter-info-card" style="border-radius: 15px; overflow: hidden; animation: fadeInUp 0.5s ease-out;">
                            <div class="card-body p-4">
                                <div class="d-flex align-items-center">
                                    <div class="newsletter-icon-container me-4" style="width: 60px; height: 60px; background-color: rgba(13, 202, 240, 0.1); border-radius: 50%; display: flex; align-items: center; justify-content: center;">
                                        <i class="fas fa-info-circle text-info" style="font-size: 2rem;"></i>
                                    </div>
                                    <div>
                                        <h5 class="card-title mb-2 fw-bold">Information</h5>
                                        <p class="card-text mb-0 text-muted">${response.message}</p>
                                    </div>
                                </div>
                            </div>
                        </div>`;
                }
                messageContainer.html(messageHtml);
                
                // Add CSS animation if not already present
                if (!$('#newsletter-animations').length) {
                    $('head').append(`
                        <style id="newsletter-animations">
                            @keyframes fadeInUp {
                                from {
                                    opacity: 0;
                                    transform: translateY(20px);
                                }
                                to {
                                    opacity: 1;
                                    transform: translateY(0);
                                }
                            }
                        </style>
                    `);
                }
            },
            error: function(xhr) {
                let errorMessage = 'An error occurred. Please try again.';
                if (xhr.responseJSON && xhr.responseJSON.message) {
                    errorMessage = xhr.responseJSON.message;
                }
                messageContainer.html(`
                    <div class="card border-0 shadow-lg newsletter-error-card" style="border-radius: 15px; overflow: hidden; animation: fadeInUp 0.5s ease-out;">
                        <div class="card-body p-4">
                            <div class="d-flex align-items-center">
                                <div class="newsletter-icon-container me-4" style="width: 60px; height: 60px; background-color: rgba(220, 53, 69, 0.1); border-radius: 50%; display: flex; align-items: center; justify-content: center;">
                                    <i class="fas fa-exclamation-circle text-danger" style="font-size: 2rem;"></i>
                                </div>
                                <div>
                                    <h5 class="card-title mb-2 fw-bold">Error</h5>
                                    <p class="card-text mb-0 text-muted">${errorMessage}</p>
                                </div>
                            </div>
                        </div>
                    </div>`);
            },
            complete: function() {
                // Re-enable submit button and restore original text
                submitBtn.prop('disabled', false).html('Subscribe');
            }
        });
        
        return false; // Prevent form submission
    });
}); 