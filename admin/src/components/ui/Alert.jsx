import React from 'react';

export const Alert = ({ 
  children, 
  className = '',
  variant = 'default'
}) => {
  const baseClasses = 'flex items-start p-4 rounded-md border';
  
  const variants = {
    default: 'bg-blue-50 border-blue-200 text-blue-800',
    success: 'bg-green-50 border-green-200 text-green-800',
    warning: 'bg-yellow-50 border-yellow-200 text-yellow-800',
    error: 'bg-red-50 border-red-200 text-red-800'
  };
  
  return (
    <div className={`${baseClasses} ${variants[variant]} ${className}`}>
      {children}
    </div>
  );
};

export const AlertDescription = ({ 
  children, 
  className = '' 
}) => (
  <div className={`flex-1 ml-3 text-sm ${className}`}>
    {children}
  </div>
);