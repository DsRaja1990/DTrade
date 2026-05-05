import React from 'react';

interface AlertProps {
  className?: string;
  children: React.ReactNode;
}

interface AlertDescriptionProps {
  className?: string;
  children: React.ReactNode;
}

export const Alert: React.FC<AlertProps> = ({ className = '', children }) => {
  return (
    <div className={`relative w-full rounded-lg border p-4 [&>svg~*]:pl-7 [&>svg+div]:translate-y-[-3px] [&>svg]:absolute [&>svg]:left-4 [&>svg]:top-4 [&>svg]:text-gray-950 ${className}`}>
      {children}
    </div>
  );
};

export const AlertDescription: React.FC<AlertDescriptionProps> = ({ className = '', children }) => {
  return (
    <div className={`text-sm [&_p]:leading-relaxed ${className}`}>
      {children}
    </div>
  );
};
