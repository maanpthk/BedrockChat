import React, { useRef } from 'react';
import { useTranslation } from 'react-i18next';
import ButtonCopy from './ButtonCopy';
import ButtonDownload from './ButtonDownload';
import { VideoGenerationResponseContent } from '../@types/conversation';

type Props = {
  content: VideoGenerationResponseContent;
};

const GeneratedVideoDisplay: React.FC<Props> = ({ content }) => {
  const { t } = useTranslation();
  const videoRef = useRef<HTMLVideoElement>(null);

  const videoUrl = `data:${content.mediaType};base64,${content.videoData}`;

  const handleDownload = () => {
    const link = document.createElement('a');
    link.href = videoUrl;
    link.download = `generated-video-${Date.now()}.mp4`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handlePlayPause = () => {
    if (videoRef.current) {
      if (videoRef.current.paused) {
        videoRef.current.play();
      } else {
        videoRef.current.pause();
      }
    }
  };

  return (
    <div className="space-y-3">
      <div className="relative group">
        <video
          ref={videoRef}
          src={videoUrl}
          className="max-w-full h-auto rounded-lg shadow-lg"
          controls
          loop
          muted
          playsInline
        />
        <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity">
          <div className="flex space-x-2">
            <ButtonCopy text={videoUrl} />
            <ButtonDownload onClick={handleDownload} />
          </div>
        </div>
      </div>

      <div className="text-sm text-gray-600 dark:text-gray-400 space-y-1">
        <div>
          <strong>{t('videoGeneration.prompt')}:</strong> {content.prompt}
        </div>
        <div>
          <strong>{t('videoGeneration.duration')}:</strong> {content.durationSeconds}s
        </div>
        {content.seed && (
          <div>
            <strong>{t('videoGeneration.seed')}:</strong> {content.seed}
          </div>
        )}
      </div>

      <div className="flex space-x-2">
        <button
          onClick={handlePlayPause}
          className="px-3 py-1 text-sm bg-blue-500 text-white rounded hover:bg-blue-600 transition-colors"
        >
          {t('videoGeneration.playPause')}
        </button>
      </div>
    </div>
  );
};

export default GeneratedVideoDisplay;