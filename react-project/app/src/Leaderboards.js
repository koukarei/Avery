import axios from 'axios';

async function fetchData() {
    try {
      const response = await fetch('https://api.example.com/data');
      const data = await response.json();
      // データを処理するコードをここに記述
    } catch (error) {
      console.error('リクエストエラー:', error);
    }
  }
  fetchData();
  