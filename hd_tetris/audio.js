// hd_tetris/audio.js

const AudioModule = (() => {
    let audioContext;
    const soundBuffers = {};
    // ※ 動作には 'sounds/' フォルダとwav/mp3ファイルが必要です。
    const audioFiles = {
        rotate: 'sounds/rotate.wav',
        lineClear: 'sounds/clear.mp3',
        bgm: 'sounds/tetris_theme.mp3'
    };

    const init = async () => {
        audioContext = new (window.AudioContext || window.webkitAudioContext)();
        // BGM停止関数を定義するためにグローバルにアクセス可能なbgmSourceを管理
        await loadAllSounds();
        playBGM();
    };

    const loadSound = async (name, url) => {
        const response = await fetch(url);
        const arrayBuffer = await response.arrayBuffer();
        soundBuffers[name] = await audioContext.decodeAudioData(arrayBuffer);
    };

    const loadAllSounds = async () => {
        const promises = Object.keys(audioFiles).map(name => loadSound(name, audioFiles[name]));
        await Promise.all(promises);
        console.log("Audio files loaded.");
    };

    const playSound = (name) => {
        if (!soundBuffers[name]) return;
        const source = audioContext.createBufferSource();
        source.buffer = soundBuffers[name];
        source.connect(audioContext.destination);
        source.start(0);
    };

    let bgmSource = null;
    const playBGM = () => {
        if (!soundBuffers.bgm) return;
        bgmSource = audioContext.createBufferSource();
        bgmSource.buffer = soundBuffers.bgm;
        bgmSource.loop = true;
        bgmSource.connect(audioContext.destination);
        bgmSource.start(0);
    };
    
    const stopBGM = () => {
        if (bgmSource) {
            bgmSource.stop();
            bgmSource = null;
        }
    };
    
    return { init, playSound, stopBGM };
})();

window.AudioModule = AudioModule;