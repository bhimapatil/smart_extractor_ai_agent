import React, { useState, useEffect } from "react";

export const LineByLineDisplay = ({ data }) => {
//   const [currentIndex, setCurrentIndex] = useState(0); 
//   const [visibleData, setVisibleData] = useState([]); 

//   useEffect(() => {
//     if (currentIndex < data.length) {
//       const timer = setInterval(() => {
//         setVisibleData((prev) => [...prev, data[currentIndex]]);
//         setCurrentIndex((prev) => prev + 1);
//       }, 400);

//       return () => clearInterval(timer); // Cleanup on unmount
//     }
//   }, [currentIndex, data]);

  return (
    <div  >
          <pre>{data}</pre>
        </div>
  );
};