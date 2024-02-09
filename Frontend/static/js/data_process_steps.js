document
  .getElementById("file-form")
  .addEventListener("submit", function (event) {
    // Define the steps
    var steps = document.querySelectorAll(".steps .step");

    // Update the first step to step-primary
    steps[0].classList.add("step-primary");

    // Check if any step has the class 'step-primary'
    var hasPrimaryStep = Array.from(steps).some(step => step.classList.contains("step-primary"));

    // If a step with class 'step-primary' is found, show the loading spinner
    if (hasPrimaryStep) {
        const loadingSpinner = document.getElementById("loading-spinner");
        loadingSpinner.classList.remove("hidden");
    }
  });

  document.body.addEventListener("htmx:afterRequest", function(event) {
    // Define the steps
    var steps = document.querySelectorAll(".steps .step");

    // Check if any step has the class 'step-error'
    var hasErrorStep = Array.from(steps).some(step => step.classList.contains("step-error"));
    //check if all steps are step-success
    var allStepsSuccess = Array.from(steps).every(step => step.classList.contains("step-success"));

    // If a step with class 'step-error' is found, handle it
    if (hasErrorStep || allStepsSuccess) {
        const loadingSpinner = document.getElementById("loading-spinner");
        loadingSpinner.classList.add("hidden");
    }
});

