$(document).ready(function() {
    // Initialize notification count
    updateNotificationCount();
    
    // Setup polling for new notifications
    setInterval(updateNotificationCount, 60000); // Check every minute
    
    // Handle marking individual notifications as read
    $('.mark-read-form').on('submit', function(e) {
        e.preventDefault();
        
        var form = $(this);
        var url = form.attr('action');
        
        $.ajax({
            url: url,
            type: 'POST',
            data: form.serialize(),
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            },
            success: function(response) {
                // Find the parent notification item and remove unread class
                form.closest('.notification-item').removeClass('unread');
                // Hide the mark as read button
                form.hide();
                // Update notification count
                updateNotificationCount();
            }
        });
    });
    
    // Handle clicking on notification items in dropdown
    $(document).on('click', '.notification-dropdown-menu .notification-item', function(e) {
        var notificationId = $(this).data('notification-id');
        var link = $(this).attr('href');
        
        if ($(this).hasClass('unread')) {
            e.preventDefault();
            
            // Mark as read via AJAX
            $.ajax({
                url: '/notifications/' + notificationId + '/mark-read/',
                type: 'POST',
                data: {
                    'csrfmiddlewaretoken': $('meta[name="csrf-token"]').attr('content')
                },
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                },
                success: function() {
                    // Redirect to the notification link
                    if (link && link !== '#') {
                        window.location.href = link;
                    }
                }
            });
        }
    });
    
    // Handle mark all as read
    $('.mark-all-read-btn').on('click', function(e) {
        e.preventDefault();
        
        $.ajax({
            url: '/notifications/mark-all-read/',
            type: 'POST',
            data: {
                'csrfmiddlewaretoken': $('meta[name="csrf-token"]').attr('content')
            },
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            },
            success: function() {
                // Remove unread class from all notification items
                $('.notification-item.unread').removeClass('unread');
                // Update notification count
                updateNotificationCount();
                // Hide the mark all as read button
                $('.mark-all-read-btn').hide();
                // Close dropdown
                $('#notificationDropdown').dropdown('hide');
            }
        });
    });
    
    // Function to update notification count
    function updateNotificationCount() {
        $.ajax({
            url: '/notifications/get-unread-count/',
            type: 'GET',
            success: function(response) {
                // Update counter in navbar
                var count = response.count;
                $('#notificationCounter').text(count);
                
                // Show/hide the badge based on count
                if (count > 0) {
                    $('#notificationBadge').text(count).show();
                    // Add pulse animation if there are new notifications
                    $('#notificationBell').addClass('pulse');
                } else {
                    $('#notificationBadge').hide();
                    // Remove pulse animation if no new notifications
                    $('#notificationBell').removeClass('pulse');
                }
                
                // Update notification dropdown if open
                if ($('.notification-dropdown-menu').hasClass('show')) {
                    refreshNotificationDropdown();
                }
            }
        });
    }
    
    // Function to refresh the notification dropdown
    function refreshNotificationDropdown() {
        $.ajax({
            url: '/notifications/get-recent-notifications/',
            type: 'GET',
            success: function(response) {
                // Update notification list
                var notificationList = $('#notificationList');
                notificationList.empty();
                
                if (response.notifications.length > 0) {
                    $.each(response.notifications, function(index, notification) {
                        var notificationIcon = getNotificationIcon(notification.type);
                        var iconClass = notification.type.toLowerCase();
                        
                        var item = $('<a>', {
                            href: notification.link || '#',
                            class: 'dropdown-item notification-item unread',
                            'data-notification-id': notification.id
                        });
                        
                        var icon = $('<div>', {
                            class: 'notification-icon ' + iconClass
                        }).append($('<i>', {
                            class: 'fas ' + notificationIcon
                        }));
                        
                        var content = $('<div>', {
                            class: 'notification-content'
                        }).append(
                            $('<div>', {
                                class: 'notification-title',
                                text: notification.title
                            }),
                            $('<div>', {
                                class: 'notification-message',
                                text: notification.message
                            }),
                            $('<div>', {
                                class: 'notification-time',
                                text: notification.created_date
                            })
                        );
                        
                        item.append(icon).append(content);
                        notificationList.append(item);
                    });
                } else {
                    var emptyMsg = $('<div>', {
                        class: 'dropdown-item text-center py-3'
                    }).append(
                        $('<div>', {
                            class: 'empty-notifications'
                        }).append(
                            $('<i>', {
                                class: 'fas fa-bell-slash mb-2 text-muted'
                            }),
                            $('<p>', {
                                class: 'mb-0 small',
                                text: 'No new notifications'
                            })
                        )
                    );
                    
                    notificationList.append(emptyMsg);
                }
                
                // Update mark all as read button visibility
                if (response.total_unread > 0) {
                    $('.mark-all-read-btn').show();
                } else {
                    $('.mark-all-read-btn').hide();
                }
            }
        });
    }
    
    // Show notification dropdown on bell click and load notifications
    $('#notificationDropdown').on('show.bs.dropdown', function() {
        refreshNotificationDropdown();
    });
    
    // Function to get icon based on notification type
    function getNotificationIcon(type) {
        var icons = {
            'System': 'fa-bell',
            'Leave': 'fa-calendar-alt',
            'Attendance': 'fa-clock',
            'Performance': 'fa-chart-line',
            'Contract': 'fa-file-contract',
            'Training': 'fa-graduation-cap',
            'Salary': 'fa-money-bill-wave',
            'Birthday': 'fa-birthday-cake',
            'Task': 'fa-tasks',
            'Document': 'fa-file-alt',
            'Expense': 'fa-receipt',
            'Asset': 'fa-laptop',
            'Workflow': 'fa-project-diagram'
        };
        
        return icons[type] || 'fa-bell';
    }
});
