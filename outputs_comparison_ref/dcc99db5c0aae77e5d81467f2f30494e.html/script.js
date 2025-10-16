function updatePreview() {
    const businessName = document.getElementById('businessName').value;
    const cardTemplate = document.getElementById('cardTemplate').value;
    const logoUpload = document.getElementById('logoUpload').files[0];

    document.getElementById('businessNamePreview').textContent = businessName;
    document.getElementById('templateImage').src = `../../../../placeholder/placeholder.png`; // Use cardTemplate logic if needed
    if (logoUpload) {
        const reader = new FileReader();
        reader.onload = function (e) {
            document.getElementById('logoPreview').src = e.target.result;
        };
        reader.readAsDataURL(logoUpload);
    } else {
        document.getElementById('logoPreview').src = '../../../../placeholder/placeholder.png';
    }
}