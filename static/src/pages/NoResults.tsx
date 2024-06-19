import React from 'react';
import CenteredCard from '../components/CenteredCard';

const NoResults: React.FC = () => {
  return (
    <CenteredCard 
      title="No Results Found for Session:" 
      text="After submission, all results are deleted. So if you are looking for old 
      results, they are no longer available" 
    />
  );
};

export default NoResults;
