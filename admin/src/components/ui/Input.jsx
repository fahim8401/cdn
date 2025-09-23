import React from 'react';

export const Input = ({ 
  type = 'text', 
  className = '', 
  placeholder = '',
  value,
  onChange,
  disabled = false,
  required = false,
  ...props 
}) => {
  const baseClasses = 'block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-blue-500 focus:border-blue-500';
  const disabledClasses = disabled ? 'bg-gray-50 cursor-not-allowed' : '';
  
  return (
    <input
      type={type}
      value={value}
      onChange={onChange}
      placeholder={placeholder}
      disabled={disabled}
      required={required}
      className={`${baseClasses} ${disabledClasses} ${className}`}
      {...props}
    />
  );
};