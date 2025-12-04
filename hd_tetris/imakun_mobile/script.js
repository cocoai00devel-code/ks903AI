// script.js

// 手順 1: HTML要素を ID を使って取得する
const messageElement = document.getElementById('message');
const buttonElement = document.getElementById('actionButton');

// 手順 2: ボタンが「クリック」されたときの動作を定義する
buttonElement.addEventListener('click', function() {
    // 手順 3: クリックされたら、メッセージの内容を変更する
    messageElement.textContent = 'ボタンが押されました！JavaScriptが動いています！';

    // (オプション) ボタン自体の見た目を変える
    buttonElement.style.backgroundColor = 'green';
});