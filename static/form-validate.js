// disable form submission if there are invalid fields (client-side validation)
(function() {
  "use strict";
  window.addEventListener("load", function() {
    // fetch the forms to apply custom Bootstrap validation styles to
    var forms = document.getElementsByClassName("validation-required");
    // loop over them and prevent submission
    var validation = Array.prototype.filter.call(forms, function(form) {
      form.addEventListener("submit", function(event) {
        if (form.checkValidity() === false) {
          event.preventDefault();
          event.stopPropagation();
        }
        form.classList.add("was-validated");
      }, false);
    });
  }, false);
})();