import { useState } from 'react';
import { UploadView } from './views/UploadView';
import { ReaderView } from './views/ReaderView';

interface LoadedFile {
  file: File;
  url: string;
}

function App() {
  const [loaded, setLoaded] = useState<LoadedFile | null>(null);

  const handleFileLoaded = (file: File, url: string) => {
    setLoaded({ file, url });
  };

  const handleReset = () => {
    if (loaded?.url) URL.revokeObjectURL(loaded.url);
    setLoaded(null);
  };

  if (!loaded) {
    return <UploadView onFileLoaded={handleFileLoaded} />;
  }

  return (
    <ReaderView
      file={loaded.file}
      url={loaded.url}
      onReset={handleReset}
    />
  );
}

export default App;
