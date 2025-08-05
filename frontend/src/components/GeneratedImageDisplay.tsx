import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import ButtonCopy from './ButtonCopy';
import ButtonDownload from './ButtonDownload';
import { ImageGenerationResponseContent } from '../@types/conversation';

type Props = {
  content: ImageGenerationResponseContent;
};

const GeneratedImageDisplay: React.FC<Props> = ({ content }) => {
  const { t } = useTranslation();
  const [isExpanded, setIsExpanded] = useState(false);

  const imageUrl = `data:${content.mediaType};base64,${content.imageData}`;

  const handleDownload = () => {
    const link = document.createElement('a');
    link.href = imageUrl;
    link.download = `generated-image-${Date.now()}.png`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="space-y-3">
      <div className="relative group">
        <img
          src={imageUrl}
          alt={content.prompt}
          className="max-w-full h-auto rounded-lg shadow-lg cursor-pointer hover:shadow-xl transition-shadow"
          onClick={() => setIsExpanded(true)}
        />
        <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity">
          <div className="flex space-x-2">
            <ButtonCopy text={imageUrl} />
            <ButtonDownload onClick={handleDownload} />
          </div>
        </div>
      </div>

      <div className="text-sm text-gray-600 dark:text-gray-400 space-y-1">
        <div>
          <strong>{t('imageGeneration.prompt')}:</strong> {content.prompt}
        </div>
        {content.seed && (
          <div>
            <strong>{t('imageGeneration.seed')}:</strong> {content.seed}
          </div>
        )}
      </div>

      {/* Expanded view modal */}
      {isExpanded && (
        <div
          className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50 p-4"
          onClick={() => setIsExpanded(false)}
        >
          <div className="relative max-w-full max-h-full">
            <img
              src={imageUrl}
              alt={content.prompt}
              className="max-w-full max-h-full object-contain"
              onClick={(e) => e.stopPropagation()}
            />
            <button
              className="absolute top-4 right-4 text-white bg-black bg-opacity-50 rounded-full w-8 h-8 flex items-center justify-center hover:bg-opacity-75"
              onClick={() => setIsExpanded(false)}
            >
              ×
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default GeneratedImageDisplay;