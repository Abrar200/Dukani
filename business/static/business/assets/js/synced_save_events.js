// Function to update heart icons
function updateHeartIcon(eventId, isSaved) {
    const heartIcons = document.querySelectorAll(`.save-button[data-event-id="${eventId}"] i`);
    heartIcons.forEach(icon => {
        if (isSaved) {
            icon.classList.remove('ph-heart', 'text-gray-600');
            icon.classList.add('ph-heart-fill', 'text-red-600');
        } else {
            icon.classList.remove('ph-heart-fill', 'text-red-600');
            icon.classList.add('ph-heart', 'text-gray-600');
        }
    });
}

// Function to handle save/unsave action
function handleSaveEvent(eventId) {
    fetch(`/save_event/${eventId}/`, {
        method: 'GET',
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(response => response.json())
    .then(data => {
        updateHeartIcon(eventId, data.status === 'saved');
        
        // If on saved events page, remove the card if event is unsaved
        if (data.status === 'removed' && window.location.pathname.includes('saved_events')) {
            const eventCard = document.querySelector(`.event-card[data-event-id="${eventId}"]`);
            if (eventCard) {
                eventCard.remove();
            }
            // Check if there are no more saved events
            if (document.querySelectorAll('.event-card').length === 0) {
                const savedEventsList = document.getElementById('saved-events-list');
                savedEventsList.innerHTML = '<div class="text-center col-span-full"><p>You have not saved any events yet.</p></div>';
            }
        }
    })
    .catch(error => console.error('Error:', error));
}

// Add event listeners to all save buttons
document.addEventListener('DOMContentLoaded', function() {
    const saveButtons = document.querySelectorAll('.save-button');
    saveButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            const eventId = this.dataset.eventId;
            handleSaveEvent(eventId);
        });
    });
});