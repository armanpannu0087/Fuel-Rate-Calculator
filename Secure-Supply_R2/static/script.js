const supplierRows = document.querySelectorAll('.supplier-row');
const popup = document.getElementById('popup');
const closeButton = document.querySelector('#popup button');

supplierRows.forEach((supplierRow) => {
    supplierRow.addEventListener('click', () => {
        if (popup.style.display === 'none' || popup.style.display === '') {
            popup.style.display = 'block';
        } else {
            popup.style.display = 'none';
        }
    });
});

// Add a click event listener to the "Close" button
closeButton.addEventListener('click', () => {
    popup.style.display = 'none';
});


const itemsPopup = document.getElementById('popup-items');

function openItemsPopup() {
    itemsPopup.style.display = 'block';
}

function closeItemsPopup() {
    itemsPopup.style.display = 'none';
}

// Add a click event listener to the "Close" button
document.getElementById('close-items-button').addEventListener('click', closeItemsPopup);
