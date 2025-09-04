import React, { useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { JSONTree } from 'react-json-tree';

import { RelatedDocument } from '../@types/conversation';
import { getAgentName } from '../features/agent/functions/formatDescription';

const RelatedDocumentViewer: React.FC<{
  relatedDocument: Omit<RelatedDocument, 'sourceId'>;
  onClick: () => void;
}> = (props) => {
  const { t } = useTranslation();

  const content = useMemo(() => (
    props.relatedDocument.content
  ), [props.relatedDocument.content]);

  const sourceName = useMemo(() => {
    if (!props.relatedDocument.sourceName) {return undefined;}
    if (props.relatedDocument.pageNumber) {
      return `${props.relatedDocument.sourceName} (p.${props.relatedDocument.pageNumber})`;
    }
    return props.relatedDocument.sourceName;
  }, [props.relatedDocument.sourceName, props.relatedDocument.pageNumber]);

  const sourceLink = useMemo(() => {
    if (!props.relatedDocument.sourceLink) {return undefined;}
    if (props.relatedDocument.pageNumber) {
      return `${props.relatedDocument.sourceLink}#page=${props.relatedDocument.pageNumber}`;
    }
    return props.relatedDocument.sourceLink;
  }, [props.relatedDocument.sourceLink, props.relatedDocument.pageNumber]);

  return (
    <div
      className="fixed left-0 top-0 z-50 flex h-dvh w-dvw items-center justify-center bg-aws-squid-ink-light/20 dark:bg-aws-squid-ink-dark/20 transition duration-1000"
      onClick={props.onClick}>
      <div
        className="max-h-[80vh] w-[70vw] max-w-[800px] overflow-y-auto rounded border bg-aws-squid-ink-light dark:bg-aws-squid-ink-dark p-1 text-sm text-aws-font-color-white-light dark:text-aws-font-color-white-dark"
        onClick={(e) => {
          e.stopPropagation();
        }}>
        {'text' in content && (
          content.text.split('\n').map((s, idx) => (
            <div key={idx}>{s}</div>
          ))
        )}
        {'json' in content && (
          <JSONTree
            data={content.json}
            invertTheme={false} // disable dark theme
          />
        )}
        {'json' in content && 
         (content as any).json && 
         typeof (content as any).json === 'object' && 
         'format' in (content as any).json && 
         'name' in (content as any).json && 
         'document' in (content as any).json && (
          <div className="flex flex-col items-center space-y-4 p-4">
            <div className="text-lg font-semibold">
              📄 {(content as any).json.name}.{(content as any).json.format}
            </div>
            <div className="text-sm text-gray-400">
              Document ready for download
            </div>
            <button
              className="px-4 py-2 bg-aws-sea-blue-light text-white rounded hover:bg-aws-sea-blue-hover-light dark:bg-aws-sea-blue-dark dark:hover:bg-aws-sea-blue-hover-dark"
              onClick={() => {
                try {
                  const docData = (content as any).json;
                  const byteCharacters = atob(docData.document);
                  const byteNumbers = new Array(byteCharacters.length);
                  for (let i = 0; i < byteCharacters.length; i++) {
                    byteNumbers[i] = byteCharacters.charCodeAt(i);
                  }
                  const byteArray = new Uint8Array(byteNumbers);
                  
                  const mimeTypes: { [key: string]: string } = {
                    'xls': 'application/vnd.ms-excel',
                    'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    'doc': 'application/msword',
                    'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                    'html': 'text/html',
                    'pdf': 'application/pdf',
                    'txt': 'text/plain',
                    'csv': 'text/csv',
                    'md': 'text/markdown'
                  };
                  
                  const mimeType = mimeTypes[docData.format] || 'application/octet-stream';
                  const blob = new Blob([byteArray], { type: mimeType });
                  const url = window.URL.createObjectURL(blob);
                  const link = window.document.createElement('a');
                  link.href = url;
                  link.download = `${docData.name}.${docData.format}`;
                  window.document.body.appendChild(link);
                  link.click();
                  window.document.body.removeChild(link);
                  window.URL.revokeObjectURL(url);
                } catch (error) {
                  console.error('Error downloading file:', error);
                }
              }}
            >
              Download File
            </button>
          </div>
        )}
        {'json' in content && 
         (content as any).json && 
         typeof (content as any).json === 'object' && 
         'media_type' in (content as any).json && 
         'image_data' in (content as any).json && 
         (content as any).json.media_type === 'image' && (
          <div className="flex flex-col items-center space-y-4 p-4">
            <div className="text-lg font-semibold">
              🖼️ Generated Image
            </div>
            <img 
              src={`data:image/png;base64,${(content as any).json.image_data}`}
              alt="Generated image"
              className="max-w-full max-h-[60vh] object-contain rounded-lg border border-gray-300 dark:border-gray-600"
            />
            {props.relatedDocument.sourceLink && (
              <button
                className="px-4 py-2 bg-aws-sea-blue-light text-white rounded hover:bg-aws-sea-blue-hover-light dark:bg-aws-sea-blue-dark dark:hover:bg-aws-sea-blue-hover-dark"
                onClick={() => window.open(props.relatedDocument.sourceLink, '_blank')}
              >
                Download Image
              </button>
            )}
          </div>
        )}
        {'json' in content && 
         (content as any).json && 
         typeof (content as any).json === 'object' && 
         'media_type' in (content as any).json && 
         (content as any).json.media_type === 'video' && (
          <div className="flex flex-col items-center space-y-4 p-4">
            <div className="text-lg font-semibold">
              🎥 Generated Video
            </div>
            {props.relatedDocument.sourceLink && (
              <video 
                controls
                className="max-w-full max-h-[60vh] rounded-lg border border-gray-300 dark:border-gray-600"
              >
                <source src={props.relatedDocument.sourceLink} type="video/mp4" />
                Your browser does not support the video tag.
              </video>
            )}
            {props.relatedDocument.sourceLink && (
              <button
                className="px-4 py-2 bg-aws-sea-blue-light text-white rounded hover:bg-aws-sea-blue-hover-light dark:bg-aws-sea-blue-dark dark:hover:bg-aws-sea-blue-hover-dark"
                onClick={() => window.open(props.relatedDocument.sourceLink, '_blank')}
              >
                Download Video
              </button>
            )}
          </div>
        )}

        {(sourceName || sourceLink) && (
          <div className="my-1 border-t pt-1 italic">
            {t('bot.label.referenceLink')}:
            {sourceLink ? (
              <span
                className="ml-1 cursor-pointer underline"
                onClick={() => {
                  window.open(sourceLink, '_blank');
                }}>
                {sourceName ? getAgentName(sourceName, t) : sourceLink}
              </span>
            ) : (
              <span className="ml-1">
                {getAgentName(sourceName!, t)}
              </span>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default RelatedDocumentViewer;
