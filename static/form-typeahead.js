// remove alerts after a while
(function() {
  "use strict";
  window.addEventListener("load", function() {
    var substringMatcher = function(strs) {
      return function findMatches(q, cb) {
        var matches, substrRegex;
        // an array that will be populated with substring matches
        matches = [];
        // regex used to determine if a string contains the substring `q`
        substrRegex = new RegExp(q, "i");
        // iterate through the pool of strings and for any string that
        // contains the substring `q`, add it to the `matches` array
        $.each(strs, function(i, str) {
          if (substrRegex.test(str)) {
            matches.push(str);
          }
        });

        cb(matches);
      };
    };

    var stocks = ["3D Systems Corporation", "3M Company", "500.com Limited", "58.com Inc.", "8x8 Inc",
      "A.H. Belo Corporation", "A.O Smith Corporation", "A10 Networks, Inc.", "AAR Corp.", "ABB Ltd", "Abbott Laboratories",
      "AbbVie Inc.", "Abercrombie & Fitch Company"
    ];

    $(".typeahead").typeahead({
      hint: true,
      highlight: true,
      minLength: 1
    },
    {
      name: "stocks",
      source: substringMatcher(stocks)
    });
      }, false);
})();