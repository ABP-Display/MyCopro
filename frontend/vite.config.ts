import {defineConfig} from 'vite';
import react from '@vitejs/plugin-react';
import {appVersion,pwaPlugin} from './pwa';
const version=appVersion();
export default defineConfig({
  define:{__APP_VERSION__:JSON.stringify(version)},
  plugins:[pwaPlugin(version),react()],
  server:{host:'0.0.0.0',proxy:{'/api':'http://127.0.0.1:8000'}},
});
