function setMobileDimensions() {
	if( /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent) ) {
		if(/Android/i.test(navigator.userAgent) && window.orientation == 90 || window.orientation == -90) {
			$('.agency-header').width(540);
			$('.wrapper').width(500);
			$('.navbar').width(480);
			('.iw_component').width(540);
		}
		else if(/webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent) && window.orientation == 0 || window.orientation == 180) {
			$('.agency-header').width(540);
            $('.wrapper').width(500);
            $('.navbar').width(480);
            $('.iw_component').width(540);
		}
	}
}