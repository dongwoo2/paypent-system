document.addEventListener('DOMContentLoaded', function() {
    document.getElementById('pay-button').addEventListener('click', function() {
        // 아임포트 결제 요청
        const IMP = window.IMP; // 아임포트 객체
        IMP.init('imp78487318'); // 아임포트 가맹점 ID

        // 결제 요청
        IMP.request_pay({
            pg: 'html5_inicis', // PG사
            pay_method: 'card', // 결제 수단
            merchant_uid: 'order_' + new Date().getTime(), // 주문 ID
            name: '주문명', // 상품명
            amount: 10000, // 결제 금액
            buyer_name: '홍길동', // 구매자 이름
            buyer_tel: '010-1234-5678', // 구매자 전화번호
            buyer_email: 'hong@example.com', // 구매자 이메일
            buyer_addr: '서울특별시', // 구매자 주소
            buyer_postcode: '123-456', // 구매자 우편번호
        }, function(rsp) {
            if (rsp.success) {
                // 결제 성공
                alert('결제가 완료되었습니다. 결제 ID: ' + rsp.imp_uid);
                // 서버에 결제 정보를 저장하는 로직 추가
            } else {
                // 결제 실패
                alert('결제에 실패하였습니다. 에러: ' + rsp.error_msg);
            }
        });
    });
});
