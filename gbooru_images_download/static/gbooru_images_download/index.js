$(".hide-btn").click(function(e) {
  e.preventDefault();

  var matchResult = $("#"+$(this).data("mr-id"))
  $.post(
      "/filteredimageurl/new/",
      { img_url: $(this).data("id"), },
      function(result, status) {
        console.log('status:' + status)
        if(status == "success") {
          matchResult.hide()
        }

      },
  );
});

var $grid = $('.grid').imagesLoaded( function() {
  // init Masonry after all images have loaded
  $grid.masonry({
    itemSelector: '.grid-item',
  });
});
