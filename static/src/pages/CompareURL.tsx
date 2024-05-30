import React from 'react';
import { useParams } from 'react-router-dom';
import CenteredCard from '../components/CenteredCard';

const CompareURL: React.FC = () => {
  const { compare_url } = useParams<{ compare_url: string }>();
  const decodedCompareUrl = decodeURIComponent(compare_url!);

  return (
    <CenteredCard 
      title="Github Comparison URL:" 
      text={decodedCompareUrl || 'Something went wrong ...'} 
    />
  );
};

export default CompareURL;
