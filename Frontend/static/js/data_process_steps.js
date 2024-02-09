
document.getElementById("file-form").addEventListener("submit", function(event) {
    // Show loading spinner
    document.getElementById("loadingSpinner").style.display = "block";

    // Define the steps
    var steps = document.querySelectorAll(".steps .step");

    // Update the first step to step-primary
    steps[0].classList.add("step-primary");

});


