// trigger form from button in table
(function() {
  "use strict";
  document.addEventListener("DOMContentLoaded", () => {
    // get the onclick event for the button
    const LIST = document.querySelectorAll(".btn");
    Array.prototype.forEach.call(LIST, (button) => {
      button.onclick = (event) => {
         // prevent default action
        event.preventDefault();
        // get -/+ direction
        const direction = event.target.getAttribute("value");
        // create a request with the FormData
        const request = new XMLHttpRequest();

        if ( direction === "+") {
          request.open("POST", "/buy_1");
        } else {
          request.open("POST", "/sell_1");
        }

        // callback for when request completed
        request.onload = () => {
          const data = JSON.parse(request.responseText);

          if (data.success) {
            if (data.transaction.quantity === 0) {
              // remove <TR> if quantity is 0
              let tr = event.target.parentElement.parentElement;
              tr.parentNode.removeChild(tr);
            } else {
              // update quantity
              let quantity = parseInt(event.target.parentNode.parentNode.querySelector(".quantity").innerText, 10);
              direction === "+" ? quantity += 1 : quantity -=1;
              event.target.parentNode.parentNode.querySelector(".quantity").innerText = quantity;
              // update price
              event.target.parentNode.parentNode.querySelector(".price").innerText = data.price;
              // update variation
              event.target.parentNode.parentNode.querySelector(".variation").innerText = data.variation;
              // update amount
              event.target.parentNode.parentNode.querySelector(".amount").innerText = data.amount;
              // update cash (<td>)
              document.querySelector("#td-cash").innerText = data.cash;
              // update grand total (<th>)
              document.querySelector("#th-total").innerText = data.grand_total;
              // update transaction data (<tr>)
              event.target.parentNode.parentNode.setAttribute("data-transaction", JSON.stringify(data.transaction));
            }
          } else {
            // error message
            const MESSAGE = data.message;
          }
        };

        // get data-* from input to build a FormData
        const formData = new FormData();
        formData.append("transaction", event.target.parentNode.parentNode.dataset.transaction);
        formData.append("grand_total", document.querySelector("#th-total").dataset.grand_total);

        // send the request to the correct route
        request.send(formData);
        // stop the page from reloading ???
        return false;
      };
    });
  }, false);
})();