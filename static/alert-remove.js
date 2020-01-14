// remove alerts after a while
(function() {
  "use strict";
  window.addEventListener("load", function() {
    // close alerts after a while
    $(".alert").delay(2000).slideUp(500, function() {
      $(this).alert("close");
    });
  }, false);
})();