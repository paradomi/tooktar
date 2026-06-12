/** 음성인식 훅 — Web Speech API 래퍼 (웹 전용, ko-KR) */
import { useCallback, useEffect, useRef, useState } from 'react';
import { Platform } from 'react-native';

// 웹 브라우저의 SpeechRecognition 생성자 (표준/웹킷 접두사)
function getSpeechRecognitionCtor(): any {
  if (Platform.OS !== 'web') return null;
  if (typeof window === 'undefined') return null;
  return (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition || null;
}

interface UseSpeechRecognitionResult {
  supported: boolean;
  listening: boolean;
  start: () => void;
  stop: () => void;
}

/** Web Speech API 기반 음성 인식. 인식 결과(중간 결과 포함)를 onResult 로 전달한다. */
export function useSpeechRecognition(onResult: (text: string) => void): UseSpeechRecognitionResult {
  const SpeechRecognitionCtor = getSpeechRecognitionCtor();
  const supported = !!SpeechRecognitionCtor;

  const [listening, setListening] = useState(false);
  const recognitionRef = useRef<any>(null);
  // stale closure 방지 — onResult 최신값을 ref 로 유지
  const onResultRef = useRef(onResult);
  onResultRef.current = onResult;

  // 언마운트 시 인식 중단
  useEffect(() => {
    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.abort();
      }
    };
  }, []);

  const stop = useCallback(() => {
    if (recognitionRef.current) {
      recognitionRef.current.stop();
    }
  }, []);

  const start = useCallback(() => {
    if (!supported || !SpeechRecognitionCtor) return;

    // 이미 듣고 있으면 중지만 한다
    if (listening) {
      stop();
      return;
    }

    try {
      const recognition = new SpeechRecognitionCtor();
      recognition.lang = 'ko-KR';
      recognition.interimResults = true;
      recognition.continuous = false;
      recognition.maxAlternatives = 1;

      recognition.onresult = (event: any) => {
        let text = '';
        for (let i = 0; i < event.results.length; i++) {
          text += event.results[i][0].transcript;
        }
        onResultRef.current(text);
      };

      recognition.onend = () => {
        setListening(false);
      };

      recognition.onerror = (event: any) => {
        setListening(false);
        if (event?.error === 'not-allowed' || event?.error === 'service-not-allowed') {
          window.alert('마이크 사용 권한을 허용해 주세요.');
        }
      };

      recognitionRef.current = recognition;
      recognition.start();
      setListening(true);
    } catch {
      setListening(false);
    }
  }, [supported, SpeechRecognitionCtor, listening, stop]);

  return { supported, listening, start, stop };
}
